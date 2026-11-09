from math import copysign

import frappe
from frappe.utils import flt, rounded

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


# When calculating tax subtotals (tax amount per tax category), we sum up line-level taxes for each category. The sum of
# subtotals should equal the total taxes nad charges. However, we sometimes get a mismatch due to floating point
# rounding. This constant describes the maximum drift we allow per line while still considering the invoice to be
# correct. I.e., If we have four lines across two categories, we allow for up to 0.04 difference between the sum of
# subtotals and the total taxes and charges, and correct the tax subtotals (see [_allocate_tax_amounts] below)
# If we get a difference larger than expected (0.04 in this example), it means we have a problem that's not related to
# rounding, and we do not attempt to correct the subtotals.
MAX_ROUNDING_DRIFT_PER_LINE = 0.01


def create_tax_total(tax_categories: dict, total_taxes_and_charges: float | None = None) -> dict:
    """Build the invoice's VAT breakdown (``cac:TaxTotal``).

    Line-level VAT comes from `Sales Invoice Item.tax_amount`, which the Saudi regional override
    recomputes per line as `flt(net_amount * rate / 100, precision)`. Rounding each line
    independently means sum(line VAT) can drift a few halalas away from `total_taxes_and_charges`.

    When we detect such drift, we recalculate subtotals and allocate the error amount (difference between expected and
    actual) into one of the subtotals. This is a workaround/hack, and it will fall apart if/when ZATCA compares
    line-level VAT to category subtotals.

    A gap too wide to be rounding is left alone; see [MAX_ROUNDING_DRIFT_PER_LINE].
    """
    amounts_by_category = {key: _get_amounts(tax_categories[key]) for key in tax_categories}
    corrected_tax_amounts_by_category = _allocate_tax_amounts(
        tax_categories, amounts_by_category, total_taxes_and_charges
    )

    tax_sub_totals = []
    tax_amount = 0
    taxable_amount = 0
    total_discount = 0
    for category in tax_categories:
        amounts = amounts_by_category[category]
        tax_sub_total = TaxSubtotal(
            taxable_amount=amounts.taxable_amount,
            tax_amount=corrected_tax_amounts_by_category[category],
            tax_category=tax_categories[category].tax_category,
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
    line_amounts = {category: amounts_by_category[category].tax_amount for category in tax_categories}
    if total_taxes_and_charges is None:
        return line_amounts

    # We round with 2-digit precision to match e_invoice.xml
    target = flt(total_taxes_and_charges, 2)
    if flt(target - sum(line_amounts.values()), 2) == 0.0:
        return line_amounts

    expected_amount_by_category = {
        category: flt(
            amounts_by_category[category].taxable_amount
            * flt(tax_categories[category].tax_category.percent or 0.0)
            / 100,
            2,
        )
        for category in tax_categories
    }
    expected_total = sum(expected_amount_by_category.values())
    if not expected_total:
        return line_amounts

    line_count = sum(len(tax_categories[category].items) for category in tax_categories)
    # Both sides are rounded: a gap of exactly one halala per line is still rounding, and an
    # unrounded float difference such as 1.31 - 1.30 = 0.010000000000000009 would exceed it.
    max_drift = flt(MAX_ROUNDING_DRIFT_PER_LINE * line_count, 2)
    if flt(abs(target - expected_total), 2) > max_drift:
        return line_amounts

    # The residue from rounding each share goes to the category carrying the most VAT
    # We recalculate all categories except the maximum one, which we assign the difference between the target VAT and
    # the sum of recalculated subtotals
    max_category: str = max(expected_amount_by_category)
    result: dict[str, float] = {
        category: flt(target * expected_amount_by_category[category] / expected_total, 2)
        for category in tax_categories
        if category != max_category
    }
    result[max_category] = flt(target - sum(result.values()), 2)
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
    # In some edge cases, such as invoices generated with precision higher than two digits, total_discount ends up
    # being `-0.0` after rounding to two-digit precision. As a temporary solution, we detect such cases, log a warning,
    # and correct the amount manually. Ideally, we should unify number handling over the invoice model since negative
    # values are prohibited except for the rounding amount.
    #
    # Note that `-0.0 == 0.0` is `True` in python, so we can't detect a negative zero with an equality check. We have
    # to check the sign.
    #
    # Also note that we do not blindly `abs` the value here to avoid hiding other bugs or unexpected scenarios that
    # could produce a negative total discount. We let them through to trigger a ZATCA validation error blocking
    # submission (if enabled) or a clear ZATCA rejection.
    if rounded(total_discount, 2) == 0.0 and copysign(1.0, total_discount) == -1.0:
        from ksa_compliance import logger

        logger.warn(f'Detected a negative discount ({total_discount}) processing {tax_category}')
        amounts.total_discount = 0.0
    else:
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
