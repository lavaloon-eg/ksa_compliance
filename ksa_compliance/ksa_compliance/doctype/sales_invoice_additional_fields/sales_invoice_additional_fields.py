# Copyright (c) 2024, Lavaloon and contributors
# For license information, please see license.txt
import hashlib
import os

import frappe
from frappe.model.document import Document
from ksa_compliance.output_models.e_invoice_output_model import Einvoice
from ksa_compliance.generate_xml import generate_xml_file
from ksa_compliance.endpoints import request_reporting_api, request_clearance_api

import uuid


class SalesInvoiceAdditionalFields(Document):
    def before_insert(self):
        self.set_invoice_counter_value()
        self.set_pih()
        self.generate_uuid()
        self.set_tax_currency()  # Set as "SAR" as a default tax currency value
        self.set_calculated_invoice_values()
        self.set_buyer_details(sl_id=self.get("sales_invoice"))
        self.set_invoice_type_code()

    def on_submit(self):
        e_invoice = self.construct_einvoice_data()
        business_setting_doc = e_invoice.business_settings_doc
        customer_id = e_invoice.sales_invoice_doc.customer

        if business_setting_doc.sync_with_zatca.lower() == "live":
            frappe.log_error("ZATCA Result LOG", message=e_invoice.result)
            frappe.log_error("ZATCA Error LOG", message=e_invoice.error_dic)
            invoice_xml = generate_xml_file(e_invoice.result)
            self.send_xml_via_api(invoice_xml=invoice_xml,
                                  business_type=business_setting_doc.type_of_business_transactions,
                                  customer_id=customer_id)

    def construct_einvoice_data(self):
        business_settings_doc = get_business_settings_doc(self.get("sales_invoice"))
        if business_settings_doc.get("type_of_business_transactions") == 'Standard Tax Invoices':
            return Einvoice(sales_invoice_additional_fields_doc=self, invoice_type="Standard")

        elif business_settings_doc.get("type_of_business_transactions") == "Simplified Tax Invoices":
            return Einvoice(sales_invoice_additional_fields_doc=self, invoice_type="Simplified")
        else:
            if self.buyer_vat_registration_number is not None or "":
                return Einvoice(sales_invoice_additional_fields_doc=self, invoice_type="Standard")
            else:
                return Einvoice(sales_invoice_additional_fields_doc=self, invoice_type="Simplified")

    def generate_uuid(self):
        self.uuid = str(uuid.uuid1())

    def set_invoice_type_code(self):
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
        self.invoice_type_transaction = "0100000" if self.buyer_vat_registration_number is None or "" else "0200000"

        is_debit, is_credit = frappe.db.get_value("Sales Invoice", self.get("sales_invoice"),
                                                  ["is_debit_note", "is_return"])
        if is_debit:
            self.invoice_type_code = "383"
        elif is_credit:
            self.invoice_type_code = "381"
        else:
            self.invoice_type_code = "383"

    def set_tax_currency(self):
        self.tax_currency = "SAR"

    def set_invoice_counter_value(self):
        additional_field_records = frappe.db.get_list(self.doctype,
                                                      filters={"docstatus": ["!=", 2],
                                                               "invoice_counter": ["is", "set"]})
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
            if attachments:  # Means that the invoice XML had been generated and saved
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

    def set_buyer_details(self, sl_id: str):
        sl = frappe.get_doc("Sales Invoice", sl_id)
        customer_doc = frappe.get_doc("Customer", sl.get("customer"))

        self.buyer_vat_registration_number = customer_doc.custom_vat_registration_number

        for item in customer_doc.get("custom_additional_ids"):
            self.append("other_buyer_ids",
                        {"type_name": item.type_name, "type_code": item.type_code, "value": item.value})

    def set_calculated_invoice_values(self):
        sinv = frappe.get_doc("Sales Invoice", self.sales_invoice)
        self.set_sum_of_charges(sinv.taxes)
        self.set_sum_of_allowances(sales_invoice_doc=sinv)

    def send_xml_via_api(self, invoice_xml, business_type: str, customer_id: str):
        if customer_has_registration(customer_id=customer_id):
            business_type = 'Standard Tax Invoices'
        else:
            business_type = 'Simplified Tax Invoices'
        if business_type == 'Simplified Tax Invoices':
            response = request_reporting_api(invoice_xml, uuid=self.get("uuid"))
            integration_dict = {"doctype": "ZATCA Integration Log",
                                "invoice_reference": self.get("sales_invoice"),
                                "invoice_additional_fields_reference": self.get("name"),
                                "zatca_message": str(response)
                                }
            integration_doc = frappe.get_doc(integration_dict)
            integration_doc.insert()
        elif business_type == 'Standard Tax Invoices':
            response = request_clearance_api(invoice_xml, uuid=self.get("uuid"))
            integration_dict = {"doctype": "ZATCA Integration Log",
                                "invoice_reference": self.get("sales_invoice"),
                                "invoice_additional_fields_reference": self.name,
                                "zatca_message": str(response)
                                }
            integration_doc = frappe.get_doc(integration_dict)
            integration_doc.insert()
        else:

            pass

    def set_sum_of_charges(self, taxes: list):
        total = 0
        if taxes:
            for item in taxes:
                total = total + item.tax_amount
        self.sum_of_charges = total

    def set_sum_of_allowances(self, sales_invoice_doc):
        self.sum_of_allowances = sales_invoice_doc.get("total") - sales_invoice_doc.get("net_total")


def customer_has_registration(customer_id: str):
    customer_doc = frappe.get_doc("Customer", customer_id)
    if customer_doc.custom_vat_registration_number in (None, "") and all(
            ide.value in (None, "") for ide in customer_doc.custom_additional_ids):
        return False
    return True


def get_business_settings_doc(invoice_id: str):
    company_id = frappe.db.get_value("Sales Invoice", invoice_id,
                                     ["company"])
    company_doc = frappe.get_doc("Company", company_id)
    business_settings_id = company_id + '-' + company_doc.get("country") + '-' + company_doc.get("default_currency")
    return frappe.get_doc("ZATCA Business Settings", business_settings_id).as_dict()
