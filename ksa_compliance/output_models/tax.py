import frappe

from ksa_compliance.standard_doctypes.tax_category import map_tax_category
from .service import get_right_fieldname, dataclass_to_frappe_dict
from .models import TaxCategory, TaxCategoryByItems, TaxTotal, TaxSubtotal, AllowanceCharge

from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry


def create_tax_categories(doc: SalesInvoice | PaymentEntry, item_lines: list) -> dict:
    tax_category_map = frappe._dict()
    sales_taxes_and_charges_template = doc.get(get_right_fieldname('taxes_and_charges', doc.doctype))
    if sales_taxes_and_charges_template:
        tax_category_id = frappe.db.get_value(
            'Sales Taxes and Charges Template', sales_taxes_and_charges_template, 'tax_category'
        )
        zatca_category = frappe.db.get_value('Tax Category', tax_category_id, 'custom_zatca_category')
        tax_category_percent = frappe.db.get_value(
            'Sales Taxes and Charges', {'parent': sales_taxes_and_charges_template}, 'rate'
        )

        tax_category_id = map_tax_category(tax_category_id=tax_category_id)
        tax_category = TaxCategory(id=tax_category_id, percent=tax_category_percent, tax_scheme_id='VAT')

        for row in item_lines:
            row.tax_percent = tax_category_percent
            row.tax_category = dataclass_to_frappe_dict(tax_category)
            if doc.doctype != 'Payment Entry':
                row.tax_amount = row.amount_after_discount * (tax_category_percent / 100)
                row.rounding_amount = row.amount_after_discount + row.tax_amount

        tax_category_by_items = TaxCategoryByItems(tax_category=tax_category, items=[row for row in item_lines])
        tax_category_by_items_cls = tax_category_map.setdefault(zatca_category, tax_category_by_items)
        return tax_category_map

    check_item_tax_template(doc, item_lines)

    for row in item_lines:
        tax_category_id = map_tax_category(item_tax_template_id=row.item_tax_template)
        tax_category_percent = frappe.db.get_value(
            'Item Tax Template Detail', {'parent': row.item_tax_template}, 'tax_rate'
        )

        zatca_category = frappe.db.get_value(
            'Item Tax Template', row.item_tax_template, 'custom_zatca_item_tax_category'
        )
        tax_category = TaxCategory(id=tax_category_id, percent=tax_category_percent, tax_scheme_id='VAT')
        row.tax_percent = tax_category_percent
        row.tax_amount = row.amount_after_discount * (tax_category_percent / 100)
        row.rounding_amount = row.amount_after_discount + row.tax_amount
        row.tax_category = dataclass_to_frappe_dict(tax_category)
        tax_category_by_items = TaxCategoryByItems(tax_category=tax_category, items=[])
        tax_category_by_items_cls = tax_category_map.setdefault(zatca_category, tax_category_by_items)
        tax_category_by_items_cls.items.append(row)
    return tax_category_map


def check_item_tax_template(doc: SalesInvoice, item_lines: list) -> None:
    invalid_items = [row.item_name for row in item_lines if not row.item_tax_template]
    if invalid_items:
        frappe.throw(
            'Please Include Sales Taxes and Charges Template on invoice\n' 'Or include Item Tax Template on {0}'.format(
                ', '.join(invalid_items)
            )
        )


def create_tax_total(doc: SalesInvoice | PaymentEntry, tax_categories: dict) -> dict:
    tax_sub_totals = []
    tax_amount = 0
    taxable_amount = 0
    for key in tax_categories:
        t_amounts = _get_t_amounts(tax_categories[key])
        tax_sub_total = TaxSubtotal(
            taxable_amount=t_amounts.taxable_amount,
            tax_amount=t_amounts.tax_amount,
            tax_category=tax_categories[key].tax_category,
        )
        tax_amount += t_amounts.tax_amount
        taxable_amount += t_amounts.taxable_amount
        tax_sub_totals.append(tax_sub_total)

    return dataclass_to_frappe_dict(
        TaxTotal(tax_amount=tax_amount, taxable_amount=taxable_amount, tax_subtotal=tax_sub_totals)
    )


def _get_t_amounts(tax_category: TaxCategoryByItems) -> float:
    taxable_amount = 0
    tax_amount = 0
    t_amounts = frappe._dict()
    for row in tax_category.items:
        taxable_amount += row.net_amount
        tax_amount += row.net_amount * (tax_category.tax_category.percent / 100)
    t_amounts.taxable_amount = taxable_amount
    t_amounts.tax_amount = tax_amount

    return t_amounts


def create_allowance_charge(doc: SalesInvoice | PaymentEntry, tax_total: frappe._dict) -> list:
    allowance_charges = []
    for row in tax_total.tax_subtotal:
        proportional = row.taxable_amount / tax_total.taxable_amount
        allowance_charge = AllowanceCharge(
            tax_category=row.tax_category,
            charge_indicator='false',
            allowance_charge_reason='discount',
            amount=_getallowance_amount(doc, proportional),
        )
        allowance_charges.append(dataclass_to_frappe_dict(allowance_charge))
    return allowance_charges


def _getallowance_amount(doc: SalesInvoice | PaymentEntry, proportional: float) -> float:
    if doc.doctype == 'Payment Entry':
        # Payment Entry does not have discount amount
        return 0.0
    discount_amount = max(0, abs(doc.discount_amount))

    if not discount_amount:
        return 0.0
    return discount_amount * proportional
