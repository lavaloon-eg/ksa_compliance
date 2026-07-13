# Copyright (c) 2024, Lavaloon and Contributors
# See license.txt

from typing import cast
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from result import Err

from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import (
    SalesInvoiceAdditionalFields,
)
from ksa_compliance.zatca_api import ReportOrClearInvoiceError

REPORT_INVOICE = (
    'ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields.api'
    '.report_invoice'
)


class TestSalesInvoiceAdditionalFields(FrappeTestCase):
    def test_send_xml_via_api_resends_on_unparseable_2xx_but_not_on_a_real_error(self):
        doc = cast(SalesInvoiceAdditionalFields, frappe.new_doc('Sales Invoice Additional Fields'))
        doc.invoice_doctype = 'Sales Invoice'
        doc.sales_invoice = 'SINV-TEST-0001'
        doc.uuid = 'test-uuid'

        with patch.object(SalesInvoiceAdditionalFields, '_add_integration_log_document'):
            # ZATCA answered 200 but the body wasn't parseable, so we don't actually know it accepted
            # the invoice. We shouldn't take its word for it and should retry instead.
            with patch(REPORT_INVOICE, return_value=(Err(ReportOrClearInvoiceError('', 'boom')), 200)):
                status = doc._send_xml_via_api('<xml/>', 'hash', 'Simplified', 'https://example.com', 'token', 'secret')
            self.assertEqual(status, 'Resend')
            self.assertEqual(doc.integration_status, 'Resend')

            # A real rejection should still be a rejection, not silently downgraded to Resend.
            with patch(REPORT_INVOICE, return_value=(Err(ReportOrClearInvoiceError('', 'invalid')), 400)):
                status = doc._send_xml_via_api('<xml/>', 'hash', 'Simplified', 'https://example.com', 'token', 'secret')
            self.assertEqual(status, 'Rejected')
