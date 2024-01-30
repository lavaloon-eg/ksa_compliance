# Copyright (c) 2024, Lavaloon and contributors
# For license information, please see license.txt
import hashlib
import os

import frappe
from frappe.model.document import Document
from ksa_compliance.output_models.e_invoice_output_model import Einvoice
from ksa_compliance.generate_xml import generate_xml_file

import uuid


class SalesInvoiceAdditionalFields(Document):
    def before_insert(self):
        self.set_invoice_counter_value()
        self.set_pih()
        self.generate_uuid()
        self.set_tax_currency()  # Set as "SAR" as a default tax currency value
        self.set_invoice_type_code("Simplified")  # TODO: Evaluate invoice type

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

    def set_invoice_counter_value(self):
        additional_field_records = frappe.db.get_list(self.doctype,
                                                      filters={"docstatus": ["!=", 2], "invoice_counter": ["is", "set"]})
        if additional_field_records:
            self.invoice_counter = len(additional_field_records) + 1
        else:
            self.invoice_counter = 1

    def set_pih(self):
        if self.invoice_counter == 1:
            self.previous_invoice_hash = "NWZlY2ViNjZmZmM4NmYzOGQ5NTI3ODZjNmQ2OTZjNzljMmRiYzIzOWRkNGU5MWI0NjcyOWQ3M2EyN2ZiNTdlOQ=="
        else:
            psi_id = frappe.db.get_value(self.doctype, filters={"invoice_counter": self.invoice_counter - 1},
                                         fieldname="sales_invoice")
            attachments = frappe.get_all("File", fields=("name", "file_name", "attached_to_name", "file_url"),
                                         filters={"attached_to_name": ("in", psi_id),
                                                  "attached_to_doctype": "Sales Invoice"})
            site = frappe.local.site
            for attachment in attachments:
                if attachment.file_name and attachment.file_name.endswith(".xml"):
                    xml_filename = attachment.file_name

            cwd = os.getcwd()
            file_name = cwd + '/' + site + "/public/files/" + xml_filename
            with open(file_name, "rb") as f:
                data = f.read()
                sha256hash = hashlib.sha256(data).hexdigest()
            self.previous_invoice_hash = sha256hash


def construct_einvoice_data(additional_fields_doc):
    return Einvoice(sales_invoice_additional_fields_doc=additional_fields_doc, invoice_type="Simplified")
