import xml.etree.ElementTree as Et
from typing import cast

import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from frappe.tests.utils import FrappeTestCase
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


class TestEinvoice(FrappeTestCase):
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
        # TODO: Create Items and customer and company
        # TODO: Validate inputs
        # Run these only once before all tests
        cls.company = input('Enter Complied Company ID: ') or 'KSA Demo'
        cls.customer = input('Enter Customer ID: ') or 'Simplified customer'

        items = []
        for i in range(1, 3):
            item_code = input(f'Enter Item {i} Code: ') or 'Demo Item'
            if item_code in items:
                item_code = 'Test5'
            price = flt(input(f'Enter Item {i} Price: ') or 57.38)
            items.append(
                {
                    'amount': price,
                    'base_amount': price,
                    'base_rate': price,
                    'item_code': item_code,
                    'qty': 1.0,
                    'rate': price,
                }
            )
        cls.items = items

    def tearDown(self):
        frappe.db.rollback()

    def create_invoice(self):
        return _make_invoice(getattr(self, 'company'), getattr(self, 'customer'), getattr(self, 'items'))

    def create_additional_fields(self, invoice_id: str):
        doc = SalesInvoiceAdditionalFields.create_for_invoice(invoice_id, 'Sales Invoice')
        doc.insert()
        return doc

    def test_standard_invoice(self):
        invoice = self.create_invoice()
        ignore_additional_fields_for_invoice(invoice.name)
        invoice.submit()
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
        for it in invoice.items:
            it.discount_percentage = 1.37

        ignore_additional_fields_for_invoice(invoice.name)
        invoice.submit()
        self.assert_generated_xml(self.create_additional_fields(invoice.name))

    def test_item_and_invoice_discount(self):
        invoice = self.create_invoice()
        invoice.apply_discount_on = 'Grand Total'
        invoice.additional_discount_percentage = 3.53
        for it in invoice.items:
            it.discount_percentage = 1.37

        ignore_additional_fields_for_invoice(invoice.name)
        invoice.submit()
        self.assert_generated_xml(self.create_additional_fields(invoice.name))

    def test_tax_included_standard(self):
        invoice = self.create_invoice()
        invoice.taxes[0].included_in_print_rate
        ignore_additional_fields_for_invoice(invoice.name)
        invoice.submit()
        self.assert_generated_xml(self.create_additional_fields(invoice.name))

    def test_tax_included_invoice_discount(self):
        invoice = self.create_invoice()
        invoice.taxes[0].included_in_print_rate
        invoice.apply_discount_on = 'Grand Total'
        invoice.additional_discount_percentage = 3.53
        ignore_additional_fields_for_invoice(invoice.name)
        invoice.submit()
        self.assert_generated_xml(self.create_additional_fields(invoice.name))

    def test_tax_included_item_discount(self):
        invoice = self.create_invoice()
        invoice.taxes[0].included_in_print_rate
        for it in invoice.items:
            it.discount_percentage = 1.37

        ignore_additional_fields_for_invoice(invoice.name)
        invoice.submit()
        self.assert_generated_xml(self.create_additional_fields(invoice.name))

    def test_tax_included_item_invoice_discount(self):
        invoice = self.create_invoice()
        invoice.taxes[0].included_in_print_rate
        invoice.apply_discount_on = 'Grand Total'
        invoice.additional_discount_percentage = 3.53
        for it in invoice.items:
            it.discount_percentage = 1.37

        ignore_additional_fields_for_invoice(invoice.name)
        invoice.submit()
        self.assert_generated_xml(self.create_additional_fields(invoice.name))

    def assert_generated_xml(self, additional_fields: SalesInvoiceAdditionalFields):
        additional_fields.load_from_db()
        xml_tree = Et.fromstring(additional_fields.invoice_xml)
        self.assert_zatca_rules(xml_tree)

    def assert_zatca_rules(self, tree: Et):
        self.assert_rule_BR_CO_15(tree=tree)
        self.assert_rule_BR_CO_11(tree=tree)
        self.assert_rule_BR_CO_14(tree=tree)
        self.assert_rule_BR_KSA_51(tree=tree)

    def assert_rule_BR_CO_15(self, tree: Et):
        tax_inclusive_amount = flt(tree.find('.//cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount', namespaces).text)
        tax_exclusive_amount = flt(tree.find('.//cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount', namespaces).text)
        total_tax_amount = flt(tree.find('.//cac:TaxTotal/cbc:TaxAmount', namespaces).text)
        self.assertEqual(tax_inclusive_amount, tax_exclusive_amount + total_tax_amount)

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


def _make_invoice(company: str, customer: str, items: list) -> SalesInvoice:
    invoice = cast(SalesInvoice, frappe.new_doc('Sales Invoice'))
    invoice.company = company
    invoice.customer = customer
    invoice.set_taxes()
    for it in items:
        invoice.append('items', it)
    invoice.set_missing_values()
    invoice.save()
    return invoice
