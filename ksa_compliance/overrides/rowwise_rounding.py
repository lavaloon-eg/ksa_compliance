# -*- coding: utf-8 -*-
"""
Row-wise VAT rounding for ERPNext sales docs driven by Company setting:
ZATCA Business Settings.enable_row_wise_rounding
Supported doctypes (via hooks override):
- Sales Invoice
- POS Invoice
- Sales Order
Design:
- A single mixin (RowwiseVATMixin) implements the override safely.
- Calls AccountsController.calculate_taxes_and_totals(self) explicitly (no super-recursion).
- If company flag is ON -> rewrites item_wise_tax_detail with rounded per-line VAT,
  updates tax rows & doc totals, then final trimming with proper precisions.
"""

from __future__ import annotations
from typing import Dict, Iterable, List
import json
import functools

import frappe
from frappe.utils import flt
from frappe.utils.data import rounded, cint

# parent calc explicitly (avoid MRO loops)
from erpnext.controllers.accounts_controller import AccountsController

# original doctypes
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice as _SalesInvoice
from erpnext.accounts.doctype.pos_invoice.pos_invoice import POSInvoice as _POSInvoice
from erpnext.selling.doctype.sales_order.sales_order import SalesOrder as _SalesOrder


# ------------- helpers -------------

@functools.lru_cache(maxsize=256)
def _company_rowwise_enabled(company: str) -> bool:
    """Read company flag once from ZATCA Business Settings (cached)."""
    if not company:
        return False
    enabled = frappe.get_value(
        "ZATCA Business Settings",
        {"company": company},
        "enable_row_wise_rounding",
    )
    try:
        return bool(int(enabled))
    except Exception:
        return bool(enabled)


def _safe_doc_prec(doc, fieldname: str, fallback: int = 2) -> int:
    try:
        p = doc.precision(fieldname)
        return int(p) if p is not None else fallback
    except Exception:
        return fallback


def _round_set(obj, field: str, prec: int) -> None:
    """Round obj.field to given precision if present & numeric-like."""
    if not hasattr(obj, field):
        return
    val = getattr(obj, field)
    if val is None:
        return
    try:
        setattr(obj, field, rounded(flt(val), prec))
    except Exception:
        pass


def _iter_items(doc) -> Iterable:
    items = getattr(doc, "items", None)
    return items or []


def _parse_item_detail(raw: str) -> Dict:
    if not raw:
        return {}
    try:
        return frappe.parse_json(raw) or {}
    except Exception:
        try:
            return json.loads(raw) or {}
        except Exception:
            return {}


# ------------- mixin (shared logic) -------------

class RowwiseVATMixin:
    """Shared override: safe row-wise VAT rounding controlled by company flag."""
    _RW_GUARD_ATTR = "_rw_rounding_in_progress"

    def calculate_taxes_and_totals(self) -> None:  # type: ignore[override]
        # guard against re-entry
        if getattr(self, self._RW_GUARD_ATTR, False):
            AccountsController.calculate_taxes_and_totals(self)
            return

        setattr(self, self._RW_GUARD_ATTR, True)
        try:
            # 1) Base calculation (ERPNext standard)
            AccountsController.calculate_taxes_and_totals(self)

            # 2) Company feature flag
            if not _company_rowwise_enabled(getattr(self, "company", None)):
                self._final_trim()
                return

            # 3) Row-wise VAT rounding (rewrite item_wise_tax_detail + update totals)
            self._apply_rowwise_vat_rounding()

            # 4) Final trimming
            self._final_trim()

        finally:
            setattr(self, self._RW_GUARD_ATTR, False)

    # ---------- internals ----------

    def _apply_rowwise_vat_rounding(self) -> None:
        """Rewrites tax.item_wise_tax_detail with rounded per-line VAT then updates totals."""
        currency_prec = _safe_doc_prec(self, "grand_total", fallback=2)
        base_prec = _safe_doc_prec(self, "base_grand_total", fallback=currency_prec)
        conv_rate = flt(getattr(self, "conversion_rate", 1.0)) or 1.0

        # Map item_code → list of child rows (same code may appear multiple times)
        code_to_rows: Dict[str, List] = {}
        for d in _iter_items(self):
            code_to_rows.setdefault(d.item_code, []).append(d)

        # accumulate per-row VAT across tax rows (optional if you want to store on row)
        per_row_total_vat: Dict[str, float] = {d.name: 0.0 for d in _iter_items(self)}

        total_taxes_after_round = 0.0

        for tax in (getattr(self, "taxes", None) or []):
            detail = _parse_item_detail(getattr(tax, "item_wise_tax_detail", None))
            if not detail:
                continue

            rounded_sum_this_tax = 0.0
            new_detail = {}

            def _r(x: float) -> float:
                return flt(x, currency_prec)

            for item_code, payload in detail.items():
                rows = code_to_rows.get(item_code, [])

                # 1) [[rate, amount], ...]
                if isinstance(payload, list) and payload and isinstance(payload[0], list):
                    rounded_payload = []
                    sum_for_code = 0.0
                    for pair in payload:
                        if isinstance(pair, list) and len(pair) == 2:
                            r, amt = pair
                            r_amt = _r(amt)
                            rounded_payload.append([r, r_amt])
                            sum_for_code += r_amt
                        else:
                            rounded_payload.append(pair)
                    new_detail[item_code] = rounded_payload
                    rounded_sum_this_tax += sum_for_code

                    if rows and sum_for_code:
                        total_net = sum([flt(r.get("net_amount") or r.get("amount") or 0.0) for r in rows]) or 1.0
                        for r in rows:
                            net = flt(r.get("net_amount") or r.get("amount") or 0.0)
                            share = sum_for_code * (net / total_net)
                            per_row_total_vat[r.name] = flt(per_row_total_vat.get(r.name, 0.0) + _r(share), currency_prec)

                # 2) [rate, amount]
                elif isinstance(payload, list) and len(payload) == 2 and all(isinstance(x, (int, float)) for x in payload):
                    rate, amt = payload
                    r_amt = _r(amt)
                    new_detail[item_code] = [rate, r_amt]
                    rounded_sum_this_tax += r_amt

                    if rows and r_amt:
                        total_net = sum([flt(r.get("net_amount") or r.get("amount") or 0.0) for r in rows]) or 1.0
                        for r in rows:
                            net = flt(r.get("net_amount") or r.get("amount") or 0.0)
                            share = r_amt * (net / total_net)
                            per_row_total_vat[r.name] = flt(per_row_total_vat.get(r.name, 0.0) + _r(share), currency_prec)

                # 3) amount only
                elif isinstance(payload, (int, float)):
                    r_amt = _r(payload)
                    new_detail[item_code] = r_amt
                    rounded_sum_this_tax += r_amt

                    if rows and r_amt:
                        total_net = sum([flt(r.get("net_amount") or r.get("amount") or 0.0) for r in rows]) or 1.0
                        for r in rows:
                            net = flt(r.get("net_amount") or r.get("amount") or 0.0)
                            share = r_amt * (net / total_net)
                            per_row_total_vat[r.name] = flt(per_row_total_vat.get(r.name, 0.0) + _r(share), currency_prec)

                else:
                    # unexpected payload shape → keep as-is
                    new_detail[item_code] = payload

            # write back rounded detail
            tax.item_wise_tax_detail = json.dumps(new_detail, ensure_ascii=False)

            # update tax row totals
            tax.tax_amount = flt(rounded_sum_this_tax, currency_prec)
            tax.base_tax_amount = flt(rounded_sum_this_tax * conv_rate, base_prec)

            if hasattr(tax, "total"):
                tax.total = flt(getattr(tax, "total", 0.0), currency_prec)
            if hasattr(tax, "base_total"):
                tax.base_total = flt(getattr(tax, "base_total", 0.0), base_prec)

            total_taxes_after_round += tax.tax_amount

        # optional: write per-row VAT if fields exist
        for d in _iter_items(self):
            if hasattr(d, "item_tax_amount"):
                d.item_tax_amount = flt(per_row_total_vat.get(d.name, 0.0), currency_prec)
            if hasattr(d, "base_item_tax_amount"):
                d.base_item_tax_amount = flt(per_row_total_vat.get(d.name, 0.0) * conv_rate, base_prec)

        # update doc totals
        self.total_taxes_and_charges = flt(total_taxes_after_round, currency_prec)
        net_total = flt(getattr(self, "total", 0.0), currency_prec)
        self.grand_total = flt(net_total + self.total_taxes_and_charges, currency_prec)
        self.base_grand_total = flt(self.grand_total * conv_rate, base_prec)
        self.rounded_total = self.grand_total
        self.in_words = frappe.utils.money_in_words(self.grand_total, getattr(self, "currency", None))

        # strong invariant
        assert flt(net_total + self.total_taxes_and_charges, currency_prec) == self.grand_total, \
            "Inconsistent totals after row-wise VAT rounding"

    def _final_trim(self) -> None:
        """Final rounding pass for doc/tax fields to eliminate float trails."""
        currency_prec = _safe_doc_prec(self, "grand_total", fallback=2)
        base_prec = _safe_doc_prec(self, "base_grand_total", fallback=currency_prec)

        # doc-level currency fields
        for f in [
            "total", "net_total", "total_taxes_and_charges",
            "grand_total", "rounded_total",
            "paid_amount", "write_off_amount", "change_amount",
            "discount_amount", "rounding_adjustment",
            "outstanding_amount",
        ]:
            _round_set(self, f, currency_prec)

        # doc-level base fields
        for f in [
            "base_total", "base_net_total", "base_total_taxes_and_charges",
            "base_grand_total", "base_rounded_total",
            "base_paid_amount", "base_write_off_amount",
            "base_change_amount", "base_discount_amount",
        ]:
            _round_set(self, f, base_prec)

        # per-tax rows
        for tax in (getattr(self, "taxes", None) or []):
            for f in (
                "tax_amount", "total", "tax_amount_after_discount_amount",
                "base_tax_amount", "base_total", "base_tax_amount_after_discount_amount",
            ):
                if f.startswith("base_"):
                    _round_set(tax, f, base_prec)
                else:
                    _round_set(tax, f, currency_prec)


# ------------- concrete overrides for hooks -------------

class SalesInvoiceKSA(RowwiseVATMixin, _SalesInvoice):
    """Override for Sales Invoice"""
    pass


class POSInvoiceKSA(RowwiseVATMixin, _POSInvoice):
    """Override for POS Invoice"""
    pass


class SalesOrderKSA(RowwiseVATMixin, _SalesOrder):
    """Override for Sales Order"""
    pass


__all__ = ["SalesInvoiceKSA", "POSInvoiceKSA", "SalesOrderKSA", "RowwiseVATMixin"]
