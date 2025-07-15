import frappe

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
            tax_category_id = map_tax_category(tax_category_id=tax_category_id)
            tax_category_percent = frappe.db.get_value(
                'Sales Taxes and Charges', {'parent': sales_taxes_and_charges_template}, 'rate'
            )
            zatca_category = frappe.db.get_value('Tax Category', tax_category_id, 'custom_zatca_category')
        else:
            tax_category_id = map_tax_category(item_tax_template_id=row.item_tax_template)
            tax_category_percent = frappe.db.get_value(
                'Item Tax Template Detail', {'parent': row.item_tax_template}, 'tax_rate'
            )
            zatca_category = frappe.db.get_value(
                'Item Tax Template', row.item_tax_template, 'custom_zatca_item_tax_category'
            )
        tax_category = TaxCategory(
            zatca_tax_category_id=tax_category_id, percent=tax_category_percent, tax_scheme_id='VAT'
        )

        row.tax_category = dataclass_to_frappe_dict(tax_category)
        tax_category_by_items = TaxCategoryByItems(tax_category=tax_category, items=[])
        tax_category_by_items_cls = tax_category_map.setdefault(
            zatca_category + str(tax_category_percent), tax_category_by_items
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


def create_tax_total(tax_categories: dict) -> dict:
    tax_sub_totals = []
    tax_amount = 0
    taxable_amount = 0
    total_discount = 0
    for key in tax_categories:
        amounts = _get_amounts(tax_categories[key])
        tax_sub_total = TaxSubtotal(
            taxable_amount=amounts.taxable_amount,
            tax_amount=amounts.tax_amount,
            tax_category=tax_categories[key].tax_category,
            total_discount=amounts.total_discount,
        )
        tax_amount += amounts.tax_amount
        taxable_amount += amounts.taxable_amount
        total_discount += amounts.total_discount
        tax_sub_totals.append(tax_sub_total)

    return dataclass_to_frappe_dict(
        TaxTotal(tax_amount=tax_amount, taxable_amount=taxable_amount, tax_subtotal=tax_sub_totals)
    )


def _get_amounts(tax_category: TaxCategoryByItems) -> float:
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
