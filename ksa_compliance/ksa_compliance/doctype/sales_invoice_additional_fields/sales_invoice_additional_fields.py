# Copyright (c) 2024, Lavaloon and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from ksa_compliance.output_models.business_settings_output_model import Einvoice


class SalesInvoiceAdditionalFields(Document):
    def on_submit(self):
        # Construct the EInvoice output data
        e_invoice = construct_einvoice_data(self)
        frappe.log_error("ZATCA Result LOG", message=e_invoice.result)
        frappe.log_error("ZATCA Error LOG", message=e_invoice.error_dic)


def construct_einvoice_data(additional_fields_doc):
    return Einvoice(sales_invoice_additional_fields_doc=additional_fields_doc, invoice_type="Simplified")
