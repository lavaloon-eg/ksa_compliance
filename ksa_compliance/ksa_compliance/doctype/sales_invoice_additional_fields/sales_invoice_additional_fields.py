# Copyright (c) 2024, Lavaloon and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from ksa_compliance.output_models.business_settings_output_model import Einvoice


class SalesInvoiceAdditionalFields(Document):
    def on_submit(self):
        e_invoice = Einvoice(sales_invoice_additional_fields_doc=self, invoice_type="Simplified")
        print(e_invoice.result, e_invoice.error_dic)
        frappe.log_error("ZATCA Result LOG", message=e_invoice.result)
        frappe.log_error("ZATCA Error LOG", message=e_invoice.error_dic)
