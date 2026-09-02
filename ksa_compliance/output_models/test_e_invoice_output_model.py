import xml.etree.ElementTree as Et
from enum import Enum
from typing import cast

import frappe
from erpnext.accounts.doctype.account.account import Account
from erpnext.accounts.doctype.item_tax_template.item_tax_template import ItemTaxTemplate
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.accounts.doctype.sales_taxes_and_charges_template.sales_taxes_and_charges_template import (
    SalesTaxesandChargesTemplate,
)
from erpnext.accounts.doctype.tax_category.tax_category import TaxCategory
from erpnext.selling.doctype.customer.customer import Customer
from erpnext.setup.doctype.company.company import Company
from erpnext.setup.doctype.item_group.item_group import ItemGroup
from erpnext.stock.doctype.item.item import Item
from frappe.tests import IntegrationTestCase
from frappe.utils import flt
from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import (
    SalesInvoiceAdditionalFields,
)
from ksa_compliance.standard_doctypes.sales_invoice import ignore_additional_fields_for_invoice

"""
    Main rounding scenarios appear in the following XML fields
    <Invoice> Fields
        - <cbc: TaxInclusiveAmount> = <cbc:TaxExclusiveAmount> + <cac:TaxTotal><cbc:TaxAmount>, Rule[BR-CO-15]
        - <cbc:AllowanceTotalAmount> = Sum of <cac:AllowanceCharge><cbc:Amount>, Rule[BR-CO-11]
        - <cbc:TaxAmount> = Sum of <cac:TaxSubtotal><cbc:TaxAmount> Rule[BR-CO-14]
        
    <Line> Fields
        - <cbc:RoundingAmount> = <cbc:LineExtensionAmount> + <cbc:TaxAmount> Rule[BR-KSA-51]
"""


class TestEInvoiceOutputModel(IntegrationTestCase):
    """
    Steps:
    1. create invoice
    2. create output xml
    3. read xml fields
    4. validate the rules
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.flags.ignore_permissions = True
        cls.company = _make_company()
        cls.customer = _make_customer()
        cls.items = _make_items()

    def tearDown(self):
        frappe.db.rollback()
        frappe.flags.ignore_permissions = False

    def create_invoice(self):
        return _make_invoice(getattr(self, 'company'), getattr(self, 'customer'), getattr(self, 'items'))

    def create_additional_fields(self, invoice_id: str):
        doc = SalesInvoiceAdditionalFields.create_for_invoice(invoice_id, 'Sales Invoice')
        doc.insert()
        return doc

    def test_standard_invoice(self):
        invoice = self.create_invoice()
        ignore_additional_fields_for_invoice(invoice.name)
        self.assert_generated_xml(self.create_additional_fields(invoice.name))

    def test_invoice_discount(self):
        invoice = self.create_invoice()
        invoice.apply_discount_on = 'Grand Total'
        invoice.additional_discount_percentage = 3.53

        ignore_additional_fields_for_invoice(invoice.name)
        invoice.submit()
        self.assert_generated_xml(self.create_additional_fields(invoice.name))

    def test_item_discount(self):
        invoice = self.create_invoice()
        invoice.items[0].discount_percentage = 2.362
        invoice.items[1].discount_percentage = 5.67

        ignore_additional_fields_for_invoice(invoice.name)
        invoice.submit()
        self.assert_generated_xml(self.create_additional_fields(invoice.name))

    def test_item_and_invoice_discount(self):
        invoice = self.create_invoice()
        invoice.apply_discount_on = 'Grand Total'
        invoice.additional_discount_percentage = 3.53
        invoice.items[0].discount_percentage = 2.362
        invoice.items[1].discount_percentage = 5.67

        ignore_additional_fields_for_invoice(invoice.name)
        invoice.submit()
        self.assert_generated_xml(self.create_additional_fields(invoice.name))

    def test_tax_included_standard(self):
        invoice = self.create_invoice()
        invoice.taxes[0].included_in_print_rate = 1
        ignore_additional_fields_for_invoice(invoice.name)
        invoice.submit()
        self.assert_generated_xml(self.create_additional_fields(invoice.name))

    def test_tax_included_invoice_discount(self):
        invoice = self.create_invoice()
        invoice.taxes[0].included_in_print_rate = 1
        invoice.apply_discount_on = 'Grand Total'
        invoice.additional_discount_percentage = 3.53
        ignore_additional_fields_for_invoice(invoice.name)
        invoice.submit()
        self.assert_generated_xml(self.create_additional_fields(invoice.name))

    def test_tax_included_item_discount(self):
        invoice = self.create_invoice()
        invoice.taxes[0].included_in_print_rate = 1
        invoice.items[0].discount_percentage = 2.362
        invoice.items[1].discount_percentage = 5.67

        ignore_additional_fields_for_invoice(invoice.name)
        invoice.submit()
        self.assert_generated_xml(self.create_additional_fields(invoice.name))

    def test_tax_included_item_invoice_discount(self):
        invoice = self.create_invoice()
        invoice.taxes[0].included_in_print_rate = 1
        invoice.apply_discount_on = 'Grand Total'
        invoice.additional_discount_percentage = 3.53
        invoice.items[0].discount_percentage = 2.362
        invoice.items[1].discount_percentage = 5.67

        ignore_additional_fields_for_invoice(invoice.name)
        invoice.submit()
        self.assert_generated_xml(self.create_additional_fields(invoice.name))

    def assert_generated_xml(self, additional_fields: SalesInvoiceAdditionalFields):
        additional_fields.load_from_db()
        xml_tree = Et.fromstring(additional_fields.invoice_xml)
        self.assert_zatca_rules(xml_tree)

    def assert_zatca_rules(self, tree: Et):
        self.assert_rule_BR_CO_11(tree=tree)
        self.assert_rule_BR_CO_14(tree=tree)
        self.assert_rule_BR_CO_15(tree=tree)
        self.assert_rule_BR_KSA_51(tree=tree)

    def assert_rule_BR_CO_15(self, tree: Et):
        tax_inclusive_amount = flt(tree.find('.//cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount', namespaces).text)
        tax_exclusive_amount = flt(tree.find('.//cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount', namespaces).text)
        total_tax_amount = flt(tree.find('.//cac:TaxTotal/cbc:TaxAmount', namespaces).text)
        self.assertEqual(tax_inclusive_amount, round(tax_exclusive_amount + total_tax_amount, 2))

    def assert_rule_BR_CO_11(self, tree: Et):
        allowance_total_amount = flt(tree.find('.//cac:LegalMonetaryTotal/cbc:AllowanceTotalAmount', namespaces).text)
        all_allowance_charges = tree.findall('.//cac:AllowanceCharge', namespaces)
        sum_allowance_charges = sum(
            flt(charge.find('.//cbc:Amount', namespaces).text) for charge in all_allowance_charges
        )
        self.assertEqual(allowance_total_amount, sum_allowance_charges)

    def assert_rule_BR_CO_14(self, tree: Et):
        tax_amount = flt(tree.find('.//cac:TaxTotal/cbc:TaxAmount', namespaces).text)
        tax_subtotals = tree.findall('.//cac:TaxTotal/cac:TaxSubtotal', namespaces)
        total_taxes = 0
        for subtotal in tax_subtotals:
            total_taxes += flt(subtotal.find('.//cbc:TaxAmount', namespaces).text)
        self.assertEqual(tax_amount, total_taxes)

    def assert_rule_BR_KSA_51(self, tree: Et):
        invoice_lines = tree.findall('.//cac:InvoiceLine', namespaces)
        for item in invoice_lines:
            rounding_amount = flt(item.find('.//cac:TaxTotal/cbc:RoundingAmount', namespaces).text)
            tax_amount = flt(item.find('.//cac:TaxTotal/cbc:TaxAmount', namespaces).text)
            line_extension_amount = flt(item.find('.//cbc:LineExtensionAmount', namespaces).text)
            self.assertEqual(rounding_amount, line_extension_amount + tax_amount)


namespaces = {
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
}


class _TaxTemplate(Enum):
    VAT15 = 'EInvoice VAT 15'
    VAT5 = 'EInvoice VAT 5'
    VAT0 = 'EInvoice VAT 0'


class _TaxCategory(Enum):
    standard = 'EInvoice Standard Rate'


def _make_invoice(company: Company, customer: Customer, items: list) -> SalesInvoice:
    invoice = cast(SalesInvoice, frappe.new_doc('Sales Invoice'))
    invoice.company = company.name
    invoice.currency = 'SAR'
    invoice.customer = customer.name
    for it in items:
        qty = 3
        rate = it.standard_rate
        amount = rate * qty
        invoice.append(
            'items',
            {
                'amount': amount,
                'base_amount': amount,
                'rate': rate,
                'base_rate': rate,
                'item_code': it.name,
                'qty': qty,
            },
        )

    invoice.taxes_and_charges = _TaxTemplate.VAT15.value
    invoice.insert()
    invoice.set_taxes()
    invoice.set_missing_values()
    invoice.save()
    return invoice


def _make_company() -> Company:
    company = cast(Company, frappe.new_doc('Company'))
    company.name = 'EInvoice Test Company'
    company.company = 'EInvoice Test Company'
    company.company_name = 'EInvoice Test Company'
    company.default_currency = 'SAR'
    company.insert()
    _make_tax_categories()
    _make_taxes(company.name)
    return company


def _make_tax_accounts(company: str) -> str:
    account_name = 'EInvoice Duties and Taxes'
    existing_account = frappe.db.get_value('Account', {'company': company, 'account_name': account_name}, 'name')
    if existing_account:
        return existing_account

    parent_account = frappe.get_value('Account', {'company': company, 'account_name': 'Duties and Taxes'}, 'name')
    if not parent_account:
        frappe.throw(f'Duties and Taxes account was not found for company {company}')

    account_doc = cast(Account, frappe.new_doc('Account'))
    account_doc.parent_account = parent_account
    account_doc.company = company
    account_doc.account_name = account_name
    account_doc.account_number = frappe.generate_hash(length=5)
    account_doc.account_type = 'Tax'
    account_doc.insert(ignore_permissions=True)
    return account_doc.name


def _make_customer() -> Customer:
    customer = cast(Customer, frappe.new_doc('Customer'))
    customer.name = 'EInvoice Test Customer'
    customer.customer_name = 'EInvoice Test Customer'
    customer.save()
    return customer


def _make_tax_categories():
    tax_category = cast(TaxCategory, frappe.new_doc('Tax Category'))
    tax_category.title = _TaxCategory.standard.value
    tax_category.custom_zatca_category = 'Standard rate'
    tax_category.save()


def _make_taxes(company: str):
    account_head = _make_tax_accounts(company)
    tax_templates = {
        _TaxTemplate.VAT15: 15,
        _TaxTemplate.VAT5: 5,
        _TaxTemplate.VAT0: 0,
    }

    for template, tax_rate in tax_templates.items():
        sales_template = cast(SalesTaxesandChargesTemplate, frappe.new_doc('Sales Taxes and Charges Template'))
        sales_template.title = template.value
        sales_template.company = company
        sales_template.is_default = int(template == _TaxTemplate.VAT15)

        # ERPNext permits only one enabled Sales Taxes and Charges Template per
        # Tax Category, so the standard category belongs to the default template.
        if template == _TaxTemplate.VAT15:
            sales_template.tax_category = _TaxCategory.standard.value

        sales_template.append(
            'taxes',
            {
                'charge_type': 'On Net Total',
                'account_head': account_head,
                'rate': tax_rate,
                'description': template.value,
            },
        )
        sales_template.insert(ignore_permissions=True)

        item_template = cast(ItemTaxTemplate, frappe.new_doc('Item Tax Template'))
        item_template.title = template.value
        item_template.company = company
        item_template.custom_zatca_item_tax_category = 'Standard rate'
        item_template.append(
            'taxes',
            {
                'tax_type': account_head,
                'tax_rate': tax_rate,
            },
        )
        item_template.insert(ignore_permissions=True)


def _make_items() -> list[Item]:
    def make_item_group() -> str:
        group = 'EInvoice Test Item Group'
        gr = cast(ItemGroup, frappe.new_doc('Item Group'))
        gr.name = group
        gr.item_group_name = group
        gr.save()
        return gr.name

    item_codes = [
        {'item_code': 'EInvoice Test Item 1', 'rate': 57.4853},
        {'item_code': 'EInvoice Test Item 2', 'rate': 22.8902},
        {'item_code': 'EInvoice Test Item 3', 'rate': 33.5421},
    ]
    item_group = make_item_group()
    output = []
    for it in item_codes:
        item = cast(Item, frappe.new_doc('Item'))
        item.name = it['item_code']
        item.item_code = it['item_code']
        item.standard_rate = it['rate']
        item.item_group = item_group
        item.save()
        output.append(item)
    return output
