from datetime import timedelta

from frappe.tests.utils import FrappeTestCase

from ksa_compliance.output_models.prepayment_invoice.invoice_line_factory import _format_time


class TestFormatTime(FrappeTestCase):
    def test_includes_real_seconds_instead_of_hardcoded_zero(self):
        self.assertEqual(_format_time(timedelta(hours=14, minutes=23, seconds=47)), '14:23:47')

    def test_zero_seconds(self):
        self.assertEqual(_format_time(timedelta(hours=9, minutes=5, seconds=0)), '09:05:00')

    def test_zero_pads_single_digit_components(self):
        self.assertEqual(_format_time(timedelta(hours=1, minutes=2, seconds=3)), '01:02:03')

    def test_truncates_fractional_seconds(self):
        self.assertEqual(_format_time(timedelta(hours=10, minutes=30, seconds=15, milliseconds=900)), '10:30:15')

    def test_midnight(self):
        self.assertEqual(_format_time(timedelta(hours=0, minutes=0, seconds=0)), '00:00:00')
