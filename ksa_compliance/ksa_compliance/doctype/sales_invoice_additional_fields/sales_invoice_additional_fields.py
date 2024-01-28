# Copyright (c) 2024, Lavaloon and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from ksa_compliance.output_models.e_invoice_output_model import Einvoice
from ksa_compliance.generate_xml import generate_xml_file

import uuid


class SalesInvoiceAdditionalFields(Document):
    def before_insert(self):
        self.generate_uuid()
        self.set_invoice_type_code("Simplified")  # TODO: Evaluate invoice type
        self.set_tax_currency()  # Set as "SAR" as a default tax currency value

    def on_submit(self):
        # Construct the EInvoice output data
        e_invoice = construct_einvoice_data(self)
        frappe.log_error("ZATCA Result LOG", message=e_invoice.result)
        frappe.log_error("ZATCA Error LOG", message=e_invoice.error_dic)
        generate_xml_file(e_invoice.result)

    def generate_uuid(self):
        self.uuid = uuid.uuid4()

    def set_invoice_type_code(self, invoice_type):
        """
        A code of the invoice subtype and invoices transactions.
        The invoice transaction code must exist and respect the following structure:
        - [NNPNESB] where
        - NN (positions 1 and 2) = invoice subtype: - 01 for tax invoice - 02 for simplified tax invoice.
        - P (position 3) = 3rd Party invoice transaction, 0 for false, 1 for true
        - N (position 4) = Nominal invoice transaction, 0 for false, 1 for true
        - E (position 5) = Exports invoice transaction, 0 for false, 1 for true
        - S (position 6) = Summary invoice transaction, 0 for false, 1 for true
        - B (position 7) = Self billed invoice. Self-billing is not allowed (KSA-2, position 7 cannot be ""1"") for export invoices (KSA-2, position 5 = 1).
        """
        # Basic Simplified or Tax invoice
        self.invoice_type_transaction = "0200000" if invoice_type.lower() == "simplified" else "0100000"
        self.invoice_type_code = "338"  # for Simplified Tax invoice

    def set_tax_currency(self):
        self.tax_currency = "SAR"


def construct_einvoice_data(additional_fields_doc):
    return Einvoice(sales_invoice_additional_fields_doc=additional_fields_doc, invoice_type="Simplified")
