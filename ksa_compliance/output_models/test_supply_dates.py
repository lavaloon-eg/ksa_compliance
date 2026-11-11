from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from ksa_compliance.output_models import supply_dates
from ksa_compliance.output_models.supply_dates import get_supply_date_field, get_supply_end_date_field


def _hooks(values: dict):
    return patch.object(supply_dates.frappe, 'get_hooks', side_effect=lambda name: values.get(name, []))


class TestSupplyDates(FrappeTestCase):
    def test_supply_date_defaults_to_due_date(self):
        with _hooks({}):
            self.assertEqual(get_supply_date_field(), 'due_date')

    def test_supply_end_date_not_emitted_by_default(self):
        with _hooks({}):
            self.assertIsNone(get_supply_end_date_field())

    def test_supply_date_reads_configured_field(self):
        with _hooks({'zatca_supply_date_field': ['posting_date']}):
            self.assertEqual(get_supply_date_field(), 'posting_date')

    def test_supply_end_date_reads_configured_field(self):
        with _hooks({'zatca_supply_end_date_field': ['custom_supply_end_date']}):
            self.assertEqual(get_supply_end_date_field(), 'custom_supply_end_date')

    def test_last_installed_app_wins(self):
        with _hooks({'zatca_supply_date_field': ['posting_date', 'custom_supply_date']}):
            self.assertEqual(get_supply_date_field(), 'custom_supply_date')

    def test_empty_hook_value_falls_back_to_default(self):
        with _hooks({'zatca_supply_date_field': ['']}):
            self.assertEqual(get_supply_date_field(), 'due_date')
