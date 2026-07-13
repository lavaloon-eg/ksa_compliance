# Copyright (c) 2024, Lavaloon and Contributors
# See license.txt

# import frappe
from frappe.tests.utils import FrappeTestCase

from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import (
    _get_integration_status,
)


class TestSalesInvoiceAdditionalFields(FrappeTestCase):
    def test_get_integration_status_falls_back_for_unmapped_codes(self):
        # Codes not explicitly in status_map: 2xx falls back to Accepted, everything else (including 0,
        # e.g. a network-level failure with no response) falls back to Resend
        self.assertEqual(_get_integration_status(201), 'Accepted')
        self.assertEqual(_get_integration_status(0), 'Resend')
        self.assertEqual(_get_integration_status(418), 'Resend')
