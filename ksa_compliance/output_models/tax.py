import frappe
from frappe.utils import flt

from ksa_compliance.standard_doctypes.tax_category import map_tax_category
from .service import get_right_fieldname, dataclass_to_frappe_dict
from .models import TaxCategory, TaxCategoryByItems, TaxTotal, TaxSubtotal, AllowanceCharge

from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
from ksa_compliance.invoice import get_zatca_discount_reason_by_name

from ksa_compliance.translation import ft
from ksa_compliance.throw import fthrow


def create_tax_categories(doc: SalesInvoice | PaymentEntry, item_lines: list, is_tax_included: bool) -> dict:
    tax_category_map = frappe._dict()
    sales_taxes_and_charges_template = doc.get(get_right_fieldname('taxes_and_charges', doc.doctype))
    item_tax_templates = [row.item_tax_template for row in item_lines if row.item_tax_template]
    if sales_taxes_and_charges_template and not item_tax_templates:
        tax_category_id = frappe.db.get_value(
            'Sales Taxes and Charges Template', sales_taxes_and_charges_template, 'tax_category'
        )
        if not tax_category_id:
            fthrow(
                msg=ft(
                    'Please set Tax Category on Sales Taxes and Charges Template $sales_taxes_and_charges_template.',
                    sales_taxes_and_charges_template=sales_taxes_and_charges_template,
                )
            )
        zatca_category = frappe.db.get_value('Tax Category', tax_category_id, 'custom_zatca_category')
        if not zatca_category:
            fthrow(
                msg=ft(
                    'Please set custom ZATCA category on Tax Category $tax_category_id.',
                    tax_category_id=tax_category_id,
                )
            )
        tax_category_percent = frappe.db.get_value(
            'Sales Taxes and Charges', {'parent': sales_taxes_and_charges_template}, 'rate'
        )

        tax_category_id = map_tax_category(tax_category_id=tax_category_id)
        tax_category = TaxCategory(
            zatca_tax_category_id=tax_category_id, percent=tax_category_percent, tax_scheme_id='VAT'
        )

        for row in item_lines:
            row.tax_category = dataclass_to_frappe_dict(tax_category)
        tax_category_by_items = TaxCategoryByItems(tax_category=tax_category, items=[row for row in item_lines])
        tax_category_by_items_cls = tax_category_map.setdefault(
            zatca_category + str(tax_category_percent), tax_category_by_items
        )
        return tax_category_map

    check_item_tax_template(doc, item_lines, sales_taxes_and_charges_template)

    for row in item_lines:
        if not row.item_tax_template and sales_taxes_and_charges_template:
            tax_category_id = frappe.db.get_value(
                'Sales Taxes and Charges Template', sales_taxes_and_charges_template, 'tax_category'
            )
            zatca_tax_category = map_tax_category(tax_category_id=tax_category_id)
            tax_category_percent = frappe.db.get_value(
                'Sales Taxes and Charges', {'parent': sales_taxes_and_charges_template}, 'rate'
            )
        else:
            zatca_tax_category = map_tax_category(item_tax_template_id=row.item_tax_template)
            tax_category_percent = frappe.db.get_value(
                'Item Tax Template Detail', {'parent': row.item_tax_template}, 'tax_rate'
            )
        tax_category = TaxCategory(
            zatca_tax_category_id=zatca_tax_category, percent=tax_category_percent, tax_scheme_id='VAT'
        )

        row.tax_category = dataclass_to_frappe_dict(tax_category)
        tax_category_by_items = TaxCategoryByItems(tax_category=tax_category, items=[])
        tax_category_by_items_cls = tax_category_map.setdefault(
            zatca_tax_category.tax_category_code + str(tax_category_percent), tax_category_by_items
        )
        tax_category_by_items_cls.items.append(row)
    return tax_category_map


def check_item_tax_template(doc: SalesInvoice, item_lines: list, sales_taxes_and_charges_template: str) -> None:
    invalid_items = [row.item_name for row in item_lines if not row.item_tax_template]
    if invalid_items and not sales_taxes_and_charges_template:
        frappe.throw(
            'Please Include Sales Taxes and Charges Template on invoice\nOr include Item Tax Template on {0}'.format(
                ', '.join(invalid_items)
            )
        )


# These are NOT a tolerance ZATCA grants us: BR-CO-14 is checked for exact equality, and a single
# halala of difference is rejected. They decide something else entirely, namely whether a gap
# between the invoice-level VAT and the line-derived VAT is small enough to be explained by
# per-line rounding, in which case the breakdown is safe to re-derive from the invoice-level
# amount. A wider gap means the lines and the invoice genuinely disagree, and no allocation can
# rescue that invoice, so we leave it alone rather than corrupt the breakdown.
#
# The smallest gap we always treat as rounding drift, however few lines the invoice has:
MAX_ROUNDING_DRIFT = 0.05

# Plus an allowance per item line, since ERPNext rounds each line's VAT to the currency precision
# and the error accumulates with the number of lines.
MAX_ROUNDING_DRIFT_PER_LINE = 0.01


def create_tax_total(tax_categories: dict, total_taxes_and_charges: float | None = None) -> dict:
    """Build the invoice's VAT breakdown (``cac:TaxTotal``).

    Line-level VAT comes from ``Sales Invoice Item.tax_amount``, which the Saudi regional override
    recomputes per line as ``flt(net_amount * rate / 100, precision)``. Rounding each line
    independently means Σ(line VAT) can drift a few halalas away from ``total_taxes_and_charges``,
    the figure ERPNext books to the general ledger and the one rendered as BT-110. One halala is
    enough for ZATCA to reject the invoice under BR-CO-14 (BT-110 = Σ BT-117), and the drift runs
    in both directions depending on where the per-line rounding falls.

    It also decides BR-CO-15 (BT-112 = BT-109 + BT-110). ZATCA resolves BT-110 there from the VAT
    breakdown rather than from ``cac:TaxTotal/cbc:TaxAmount``, so the same drift breaks that rule
    too whenever it happens to fall on the wrong side.

    When *total_taxes_and_charges* is given, the category amounts are therefore derived from it
    instead of from the lines, so BT-110 and Σ BT-117 cannot disagree. The share each category
    receives is proportional to the VAT that category is *expected* to carry
    (``taxable amount × rate``), never to its taxable amount alone -- otherwise a zero rated or
    exempt category would be handed VAT and fail BR-Z-09/BR-E-09, and the standard rated category
    would fail BR-CO-17.

    A gap too wide to be rounding is left alone; see [MAX_ROUNDING_DRIFT].
    """
    amounts_by_category = {key: _get_amounts(tax_categories[key]) for key in tax_categories}
    tax_amount_by_category = _allocate_tax_amounts(tax_categories, amounts_by_category, total_taxes_and_charges)

    tax_sub_totals = []
    tax_amount = 0
    taxable_amount = 0
    total_discount = 0
    for key in tax_categories:
        amounts = amounts_by_category[key]
        tax_sub_total = TaxSubtotal(
            taxable_amount=amounts.taxable_amount,
            tax_amount=tax_amount_by_category[key],
            tax_category=tax_categories[key].tax_category,
            total_discount=amounts.total_discount,
        )
        tax_amount += tax_sub_total.tax_amount
        taxable_amount += amounts.taxable_amount
        total_discount += amounts.total_discount
        tax_sub_totals.append(tax_sub_total)

    return dataclass_to_frappe_dict(
        TaxTotal(tax_amount=tax_amount, taxable_amount=taxable_amount, tax_subtotal=tax_sub_totals)
    )


def _allocate_tax_amounts(
    tax_categories: dict, amounts_by_category: dict, total_taxes_and_charges: float | None
) -> dict:
    """Decide the VAT amount (BT-117) of each tax category. See [create_tax_total] for the rules."""
    line_amounts = {key: amounts_by_category[key].tax_amount for key in tax_categories}
    if total_taxes_and_charges is None:
        return line_amounts

    # flt rounds through frappe.utils.data.rounded, which honours the system's rounding method.
    # The XML template rounds every amount the same way, so anchoring on flt keeps the breakdown
    # consistent with the BT-110 that ends up in the XML.
    target = flt(total_taxes_and_charges, 2)
    if flt(target - sum(line_amounts.values()), 2) == 0.0:
        return line_amounts

    expected = {
        key: flt(
            amounts_by_category[key].taxable_amount * flt(tax_categories[key].tax_category.percent or 0.0) / 100, 2
        )
        for key in tax_categories
    }
    expected_total = sum(expected.values())
    if not expected_total:
        return line_amounts

    line_count = sum(len(tax_categories[key].items) for key in tax_categories)
    max_drift = max(MAX_ROUNDING_DRIFT, MAX_ROUNDING_DRIFT_PER_LINE * line_count)
    if abs(target - expected_total) > max_drift:
        return line_amounts

    # The residue from rounding each share goes to the category carrying the most VAT, so it can
    # never land on a zero rated, exempt or out-of-scope category.
    residue_key = max(tax_categories, key=lambda key: expected[key])
    allocated = 0.0
    result = {}
    for key in tax_categories:
        if key == residue_key:
            continue
        result[key] = flt(target * expected[key] / expected_total, 2)
        allocated += result[key]
    result[residue_key] = flt(target - allocated, 2)
    return result


def _get_amounts(tax_category: TaxCategoryByItems) -> frappe._dict:
    taxable_amount = 0
    tax_amount = 0
    total_discount = 0
    amounts = frappe._dict()
    for row in tax_category.items:
        taxable_amount += row.net_amount
        tax_amount += row.tax_amount
        total_discount += row.amount - row.net_amount
    amounts.taxable_amount = taxable_amount
    amounts.tax_amount = tax_amount
    amounts.total_discount = total_discount

    return amounts


def create_allowance_charge(doc: SalesInvoice | PaymentEntry, tax_total: frappe._dict) -> list:
    allowance_charges = []
    discount_reason, discount_reason_code = None, None
    if doc.doctype == 'Sales Invoice' and doc.discount_amount:
        zatca_discount_reason = get_zatca_discount_reason_by_name(name=doc.custom_zatca_discount_reason)
        discount_reason = zatca_discount_reason.name
        discount_reason_code = zatca_discount_reason.code

    for row in tax_total.tax_subtotal:
        if doc.doctype == 'Payment Entry':
            row.total_discount = 0
        allowance_charge = AllowanceCharge(
            tax_category=row.tax_category,
            charge_indicator='false',
            allowance_charge_reason=discount_reason,
            allowance_charge_reason_code=discount_reason_code,
            amount=row.total_discount,
        )
        allowance_charges.append(dataclass_to_frappe_dict(allowance_charge))
    return allowance_charges
