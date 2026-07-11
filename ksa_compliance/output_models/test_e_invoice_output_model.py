# Copyright (c) 2026, LavaLoon and contributors
# For license information, please see license.txt
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ksa_compliance.output_models.e_invoice_output_model import Einvoice


def _make_einvoice(sales_invoice_doc: dict, customer_name_field: str | None) -> Einvoice:
    """
    Builds a bare Einvoice instance without running __init__, so this stays a pure unit test of
    _set_buyer_registration_name without needing Company/Customer/Sales Invoice DB fixtures.
    """
    einvoice = Einvoice.__new__(Einvoice)
    einvoice.sales_invoice_doc = frappe._dict(sales_invoice_doc)
    einvoice.business_settings_doc = frappe._dict(customer_name_field=customer_name_field)
    einvoice.result = {'buyer_details': {}}
    return einvoice


class TestEinvoiceBuyerRegistrationName(FrappeTestCase):
    def test_falls_back_to_customer_name_when_setting_is_unset(self):
        einvoice = _make_einvoice(
            {'doctype': 'Sales Invoice', 'customer': 'CUST-001', 'customer_name': 'Acme Corp'},
            customer_name_field=None,
        )
        einvoice._set_buyer_registration_name()
        self.assertEqual(einvoice.result['buyer_details']['registration_name'], 'Acme Corp')

    def test_uses_custom_field_when_set_and_populated(self):
        einvoice = _make_einvoice(
            {'doctype': 'Sales Invoice', 'customer': 'CUST-001', 'customer_name': 'Acme Corp'},
            customer_name_field='custom_customer_name_arabic',
        )
        with patch('frappe.db.get_value', return_value='شركة أكمي'):
            einvoice._set_buyer_registration_name()
        self.assertEqual(einvoice.result['buyer_details']['registration_name'], 'شركة أكمي')

    def test_falls_back_to_customer_name_when_custom_field_is_empty(self):
        einvoice = _make_einvoice(
            {'doctype': 'Sales Invoice', 'customer': 'CUST-001', 'customer_name': 'Acme Corp'},
            customer_name_field='custom_customer_name_arabic',
        )
        with patch('frappe.db.get_value', return_value=None):
            einvoice._set_buyer_registration_name()
        self.assertEqual(einvoice.result['buyer_details']['registration_name'], 'Acme Corp')

    def test_looks_up_customer_via_party_for_payment_entry(self):
        einvoice = _make_einvoice(
            {'doctype': 'Payment Entry', 'party': 'CUST-002', 'party_name': 'Beta LLC'},
            customer_name_field='custom_customer_name_arabic',
        )
        with patch('frappe.db.get_value', return_value='شركة بيتا') as mock_get_value:
            einvoice._set_buyer_registration_name()
        mock_get_value.assert_called_once_with('Customer', 'CUST-002', 'custom_customer_name_arabic')
        self.assertEqual(einvoice.result['buyer_details']['registration_name'], 'شركة بيتا')
