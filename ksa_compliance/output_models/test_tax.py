# Copyright (c) 2026, LavaLoon and Contributors
# See license.txt
"""Tests for the VAT breakdown (``cac:TaxTotal``) built by :mod:`ksa_compliance.output_models.tax`.

These tests are written against the ZATCA/EN 16931 business rules rather than against the
implementation, so they stay meaningful if the allocation strategy changes:

* **BR-CO-14** -- Invoice total VAT amount (BT-110) = Σ VAT category tax amount (BT-117)
* **BR-CO-15** -- Invoice total amount with VAT (BT-112) = Invoice total amount without VAT
  (BT-109) + Invoice total VAT amount (BT-110)
* **BR-CO-17** -- VAT category tax amount (BT-117) = VAT category taxable amount (BT-116)
  × (VAT category rate (BT-119) / 100), rounded to two decimals
* **BR-Z-09 / BR-E-09 / BR-O-09** -- a zero rated, exempt or out-of-scope category carries no VAT

Line-level ``tax_amount`` values are supplied explicitly instead of being derived, because that
is what the code under test consumes: ERPNext fills ``Sales Invoice Item.tax_amount`` through the
Saudi regional override (``erpnext.regional.united_arab_emirates.utils.update_itemised_tax_data``),
which recomputes each line as ``flt(net_amount * rate / 100, precision)``. Rounding each line
independently is exactly what makes Σ(line VAT) drift away from the invoice-level
``total_taxes_and_charges``, which is the drift these tests describe.

``REJECTED_INVOICES`` below is transcribed from invoices ZATCA rejected in production. Everything
else is constructed, and worth reading as such: no production data was available for an invoice
mixing standard rated lines with zero rated or exempt ones, so those cases assert what the rules
require rather than something observed.
"""

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import flt

from ksa_compliance.output_models.models import TaxCategory, TaxCategoryByItems, ZatcaTaxCategory
from ksa_compliance.output_models.tax import create_tax_total

# ZATCA tax category codes
STANDARD = 'S'
ZERO_RATED = 'Z'
EXEMPT = 'E'

# Invoices ZATCA rejected in production, transcribed from the XML that was submitted.
# Each entry is (invoice id, rate, [(line net, line VAT)], VAT booked by ERPNext).
#
# 05526 and 05509 price tax-inclusive, so each line's net is itself a rounded ``amount / 1.15``
# before its VAT is rounded again. 05454 prices tax-exclusive and drifts the *other* way, which
# is why it also tripped BR-CO-15 while the first two did not.
REJECTED_INVOICES = (
    ('ACC-SINV-2025-05526', 15.0, [(313.91, 47.09), (413.04, 61.96)], 109.04),
    ('ACC-SINV-2025-05509', 15.0, [(695.65, 104.35), (834.78, 125.22)], 229.56),
    (
        'ACC-SINV-2025-05454',
        15.0,
        [
            (1140.00, 171.00),
            (1477.08, 221.56),
            (919.50, 137.92),
            (190.00, 28.50),
            (125.00, 18.75),
            (120.00, 18.00),
            (40.00, 6.00),
            (35.00, 5.25),
            (105.00, 15.75),
            (132.00, 19.80),
            (279.00, 41.85),
            (406.00, 60.90),
            (163.00, 24.45),
            (126.00, 18.90),
            (235.00, 35.25),
            (75.00, 11.25),
            (104.00, 15.60),
        ],
        850.74,
    ),
)


def build_item(net_amount: float, tax_amount: float, amount: float = None) -> frappe._dict:
    """Build the minimal item line shape consumed by ``_get_amounts``."""
    return frappe._dict(
        net_amount=net_amount,
        tax_amount=tax_amount,
        amount=net_amount if amount is None else amount,
    )


def rounding_methods() -> list:
    """Every rounding method System Settings offers, falling back to the configured one."""
    field = frappe.get_meta('System Settings').get_field('rounding_method')
    options = [option.strip() for option in (field.options or '').split('\n') if option.strip()] if field else []
    return options or [frappe.get_system_settings('rounding_method')]


def build_categories(*specs) -> frappe._dict:
    """Build a tax category map from ``(key, code, percent, items)`` tuples.

    Insertion order is preserved, which matters: it is the order the invoice's item lines
    produced the categories in, and no rule may depend on it.
    """
    categories = frappe._dict()
    for key, code, percent, items in specs:
        categories[key] = TaxCategoryByItems(
            tax_category=TaxCategory(
                zatca_tax_category_id=ZatcaTaxCategory(tax_category_code=code),
                percent=percent,
                tax_scheme_id='VAT',
            ),
            items=list(items),
        )
    return categories


class TestCreateTaxTotal(FrappeTestCase):
    # --------------------------------------------------------------- assertions

    def assert_br_co_14(self, tax_total: frappe._dict, expected_vat: float):
        """BT-110 = Σ BT-117."""
        total = flt(sum(flt(row.tax_amount, 2) for row in tax_total.tax_subtotal), 2)
        self.assertEqual(
            total,
            flt(expected_vat, 2),
            msg=f'BR-CO-14 violated: Σ VAT category tax amount {total} != invoice total VAT {flt(expected_vat, 2)}',
        )

    def assert_br_co_17(self, tax_total: frappe._dict):
        """BT-117 = BT-116 × (BT-119 / 100)."""
        for row in tax_total.tax_subtotal:
            percent = flt(row.tax_category.percent or 0.0)
            expected = flt(flt(row.taxable_amount) * percent / 100, 2)
            self.assertAlmostEqual(
                flt(row.tax_amount, 2),
                expected,
                delta=0.02,
                msg=(
                    f'BR-CO-17 violated for category '
                    f'{row.tax_category.zatca_tax_category_id.tax_category_code} @ {percent}%: '
                    f'tax amount {flt(row.tax_amount, 2)} != taxable {flt(row.taxable_amount, 2)} × {percent}%'
                ),
            )

    def assert_no_vat_on_zero_rate_categories(self, tax_total: frappe._dict):
        """BR-Z-09 / BR-E-09 / BR-O-09."""
        for row in tax_total.tax_subtotal:
            if flt(row.tax_category.percent or 0.0):
                continue
            self.assertEqual(
                flt(row.tax_amount, 2),
                0.0,
                msg=(
                    f'BR-Z-09/BR-E-09 violated: category '
                    f'{row.tax_category.zatca_tax_category_id.tax_category_code} is rated at 0% but '
                    f'carries {flt(row.tax_amount, 2)} of VAT'
                ),
            )

    def assert_br_co_15(self, tax_total: frappe._dict, net_total: float, grand_total: float):
        """BT-112 = BT-109 + BT-110.

        ZATCA resolves BT-110 here from the VAT breakdown, not from ``cac:TaxTotal/cbc:TaxAmount``.
        Across the four rejected invoices we have, that reading predicts whether BR-CO-15 was
        reported in every case, while reading it from ``cac:TaxTotal`` predicts none of them.
        """
        bt110 = flt(sum(flt(row.tax_amount, 2) for row in tax_total.tax_subtotal), 2)
        self.assertEqual(
            flt(net_total + bt110, 2),
            flt(grand_total, 2),
            msg=(f'BR-CO-15 violated: BT-109 {flt(net_total, 2)} + BT-110 {bt110} != BT-112 {flt(grand_total, 2)}'),
        )

    def assert_all_rules(self, tax_total: frappe._dict, expected_vat: float):
        self.assert_br_co_14(tax_total, expected_vat)
        self.assert_br_co_17(tax_total)
        self.assert_no_vat_on_zero_rate_categories(tax_total)

    def subtotal_for(self, tax_total: frappe._dict, code: str) -> frappe._dict:
        rows = [r for r in tax_total.tax_subtotal if r.tax_category.zatca_tax_category_id.tax_category_code == code]
        self.assertEqual(len(rows), 1, msg=f'Expected exactly one {code} subtotal, found {len(rows)}')
        return rows[0]

    # --------------------------------------------------------------- test cases

    def test_invoices_rejected_by_zatca(self):
        """Invoices ZATCA actually rejected, replayed through the breakdown.

        Each one is a plain single rate invoice whose only defect is that the lines and the
        document round differently. Both drift directions are represented.
        """
        for invoice_id, rate, lines, invoice_vat in REJECTED_INVOICES:
            with self.subTest(invoice=invoice_id):
                line_vat = flt(sum(vat for _, vat in lines), 2)
                self.assertNotEqual(
                    line_vat,
                    flt(invoice_vat, 2),
                    msg=f'{invoice_id} is meant to be a drift case, but the lines already agree',
                )

                categories = build_categories(('S', STANDARD, rate, [build_item(net, vat) for net, vat in lines]))
                tax_total = create_tax_total(categories, invoice_vat)

                net_total = flt(sum(net for net, _ in lines), 2)
                self.assert_all_rules(tax_total, invoice_vat)
                # BT-112 as the XML builds it: BT-109 + the invoice level VAT.
                self.assert_br_co_15(tax_total, net_total, flt(net_total + invoice_vat, 2))

    def test_single_category_without_drift_is_unchanged(self):
        """Baseline: when the line VAT already agrees with the invoice VAT, nothing moves."""
        categories = build_categories(('S15', STANDARD, 15.0, [build_item(1000.00, 150.00)]))

        tax_total = create_tax_total(categories, 150.00)

        self.assert_all_rules(tax_total, 150.00)
        self.assertEqual(flt(self.subtotal_for(tax_total, STANDARD).taxable_amount, 2), 1000.00)

    def test_single_category_absorbs_per_line_rounding_drift(self):
        """Per-line rounding makes Σ(line VAT) 4.56 while ERPNext booked 4.54. BT-117 must follow BT-110.

        Fails on master, where the subtotal is taken straight from Σ(line VAT).
        """
        categories = build_categories(
            (
                'S15',
                STANDARD,
                15.0,
                [build_item(10.10, 1.52), build_item(10.10, 1.52), build_item(10.10, 1.52)],
            )
        )

        tax_total = create_tax_total(categories, 4.54)

        self.assert_all_rules(tax_total, 4.54)
        self.assertEqual(flt(self.subtotal_for(tax_total, STANDARD).tax_amount, 2), 4.54)

    def test_standard_and_zero_rated_keep_vat_on_the_standard_category(self):
        """A zero rated category must never be handed VAT, no matter how the residue is distributed.

        Fails on any allocator that distributes the invoice VAT in proportion to *taxable amount*
        rather than to *expected VAT*: that splits 150.00 into 75.00 / 75.00.
        """
        categories = build_categories(
            ('S15', STANDARD, 15.0, [build_item(1000.00, 150.00)]),
            ('Z0', ZERO_RATED, 0.0, [build_item(1000.00, 0.00)]),
        )

        tax_total = create_tax_total(categories, 150.00)

        self.assert_all_rules(tax_total, 150.00)
        self.assertEqual(flt(self.subtotal_for(tax_total, STANDARD).tax_amount, 2), 150.00)
        self.assertEqual(flt(self.subtotal_for(tax_total, ZERO_RATED).tax_amount, 2), 0.00)

    def test_drift_residue_lands_on_the_standard_category_not_the_exempt_one(self):
        """Σ(line VAT) is 15.01 but ERPNext booked 15.00; the exempt category must stay at 0.00.

        Fails on master (BR-CO-14: 15.01 != 15.00) *and* on a taxable-weighted allocator, which
        hands 5.00 of VAT to the exempt category because it holds a third of the taxable amount.
        """
        categories = build_categories(
            ('S15', STANDARD, 15.0, [build_item(33.33, 5.00), build_item(66.67, 10.01)]),
            ('E0', EXEMPT, 0.0, [build_item(50.00, 0.00)]),
        )

        tax_total = create_tax_total(categories, 15.00)

        self.assert_all_rules(tax_total, 15.00)
        self.assertEqual(flt(self.subtotal_for(tax_total, STANDARD).tax_amount, 2), 15.00)
        self.assertEqual(flt(self.subtotal_for(tax_total, EXEMPT).tax_amount, 2), 0.00)

    def test_two_non_zero_rates_are_weighted_by_rate_not_by_taxable_amount(self):
        """Equal taxable amounts at 15% and 5% must keep their 150/50 split, not become 100/100.

        Fails on a taxable-weighted allocator (BR-CO-17: 100.00 != 1000.00 × 15%).
        """
        categories = build_categories(
            ('S15', STANDARD, 15.0, [build_item(1000.00, 150.00)]),
            ('S5', STANDARD, 5.0, [build_item(1000.00, 50.00)]),
        )

        tax_total = create_tax_total(categories, 199.99)

        self.assert_br_co_14(tax_total, 199.99)
        self.assert_br_co_17(tax_total)
        by_rate = {flt(r.tax_category.percent): flt(r.tax_amount, 2) for r in tax_total.tax_subtotal}
        self.assertAlmostEqual(by_rate[15.0], 150.00, delta=0.02)
        self.assertAlmostEqual(by_rate[5.0], 50.00, delta=0.02)

    def test_omitting_the_invoice_vat_preserves_line_derived_amounts(self):
        """Payment Entry adjusts its VAT after the breakdown is built, so it passes no anchor.

        Guards against the breakdown being pinned to a figure the template will later override.
        """
        categories = build_categories(
            ('S15', STANDARD, 15.0, [build_item(10.10, 1.52), build_item(10.10, 1.52), build_item(10.10, 1.52)])
        )

        tax_total = create_tax_total(categories)

        self.assertEqual(flt(self.subtotal_for(tax_total, STANDARD).tax_amount, 2), 4.56)

    def test_fully_zero_rated_invoice(self):
        """An invoice with no VAT at all must not divide by zero."""
        categories = build_categories(
            ('Z0', ZERO_RATED, 0.0, [build_item(1000.00, 0.00)]),
            ('E0', EXEMPT, 0.0, [build_item(500.00, 0.00)]),
        )

        tax_total = create_tax_total(categories, 0.00)

        self.assert_all_rules(tax_total, 0.00)

    def test_structural_mismatch_is_not_silently_absorbed(self):
        """A gap far beyond rounding (here a grand total discount) must not be papered over.

        ERPNext booked 100.00 of VAT while the lines, which are not discounted, imply 150.00.
        Redistributing would hide a real data problem behind a BR-CO-17 violation, so the
        breakdown stays line-derived and lets ZATCA report the underlying inconsistency.
        """
        categories = build_categories(('S15', STANDARD, 15.0, [build_item(1000.00, 150.00)]))

        tax_total = create_tax_total(categories, 100.00)

        self.assertEqual(flt(self.subtotal_for(tax_total, STANDARD).tax_amount, 2), 150.00)
        self.assert_br_co_17(tax_total)

    def test_drift_absorbed_under_every_rounding_method(self):
        """The XML renders every amount through ``frappe.utils.data.rounded``, which honours the
        system's rounding method, so the breakdown has to agree with that rather than with Python's
        ``round``. Every configurable method is exercised.
        """
        methods = rounding_methods()
        self.assertTrue(methods, msg='System Settings offers no rounding method to exercise')
        for method in methods:
            with self.subTest(rounding_method=method), change_settings('System Settings', rounding_method=method):
                categories = build_categories(
                    (
                        'S15',
                        STANDARD,
                        15.0,
                        [build_item(10.10, 1.52), build_item(10.10, 1.52), build_item(10.10, 1.52)],
                    )
                )

                tax_total = create_tax_total(categories, 4.54)

                self.assert_all_rules(tax_total, 4.54)
