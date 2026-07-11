import datetime
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from ksa_compliance.background_jobs import (
    STUCK_INVOICE_THRESHOLD_HOURS,
    add_batch_to_background_queue,
    find_stuck_invoices,
)


class TestAddBatchToBackgroundQueue(FrappeTestCase):
    @patch('ksa_compliance.background_jobs.frappe.enqueue')
    def test_uses_current_date_at_call_time(self, mock_enqueue):
        # The old implementation used check_date=datetime.date.today() as a default value, which is
        # evaluated once at import time. This subclass simulates the passage of time between two calls
        # to prove the date is now resolved fresh on each call, not frozen at definition time.
        class FixedDate(datetime.date):
            fixed = datetime.date(2024, 1, 1)

            @classmethod
            def today(cls):
                return cls.fixed

        with patch('ksa_compliance.background_jobs.datetime.date', FixedDate):
            add_batch_to_background_queue()
        first_call_date = mock_enqueue.call_args.kwargs['check_date']

        FixedDate.fixed = datetime.date(2024, 6, 1)
        with patch('ksa_compliance.background_jobs.datetime.date', FixedDate):
            add_batch_to_background_queue()
        second_call_date = mock_enqueue.call_args.kwargs['check_date']

        self.assertEqual(first_call_date, datetime.date(2024, 1, 1))
        self.assertEqual(second_call_date, datetime.date(2024, 6, 1))


class TestFindStuckInvoices(FrappeTestCase):
    def setUp(self):
        self.created_names = []

    def tearDown(self):
        for name in self.created_names:
            frappe.db.delete('Sales Invoice Additional Fields', {'name': name})

    def _make_siaf(self, name: str, integration_status: str, docstatus: int, age_hours: float):
        # Raw SQL bypasses Sales Invoice Additional Fields' insert/validate hooks (invoice counter,
        # PIH chain, ZATCA Business Settings lookups), which need a real, fully-formed Sales Invoice
        # and aren't relevant to testing find_stuck_invoices' status/docstatus/threshold filtering.
        creation = now_datetime() - datetime.timedelta(hours=age_hours)
        frappe.db.sql(
            """
            insert into `tabSales Invoice Additional Fields`
                (name, creation, modified, owner, modified_by, docstatus, integration_status, sales_invoice)
            values (%(name)s, %(creation)s, %(creation)s, 'Administrator', 'Administrator', %(docstatus)s,
                    %(status)s, %(name)s)
            """,
            {'name': name, 'creation': creation, 'docstatus': docstatus, 'status': integration_status},
        )
        self.created_names.append(name)

    def test_respects_status_docstatus_and_threshold(self):
        old_hours = STUCK_INVOICE_THRESHOLD_HOURS + 1
        fresh_hours = STUCK_INVOICE_THRESHOLD_HOURS - 1

        self._make_siaf('test-stuck-old-draft', 'Resend', 0, old_hours)
        self._make_siaf('test-stuck-fresh-draft', 'Ready For Batch', 0, fresh_hours)
        self._make_siaf('test-stuck-old-submitted', 'Ready For Batch', 1, old_hours)
        self._make_siaf('test-stuck-old-ineligible-status', 'Rejected', 0, old_hours)

        stuck_names = {row.name for row in find_stuck_invoices()}

        self.assertIn('test-stuck-old-draft', stuck_names)
        self.assertNotIn('test-stuck-fresh-draft', stuck_names)
        self.assertNotIn('test-stuck-old-submitted', stuck_names)
        self.assertNotIn('test-stuck-old-ineligible-status', stuck_names)
