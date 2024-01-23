# Copyright (c) 2024, Lavaloon and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from ksa_compliance.output_models.business_settings_output_model import Einvoice


class SalesInvoiceAdditionalFields(Document):
    def on_submit(self):
        result, error = Einvoice(sales_invoice_additional_fields_doc=self, invoice_type="Simplified")
        if error:
            asd
