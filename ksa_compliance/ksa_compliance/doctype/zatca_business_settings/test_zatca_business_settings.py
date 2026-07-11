# Copyright (c) 2024, Lavaloon and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import (
    ZATCABusinessSettings,
)


class TestZATCABusinessSettings(FrappeTestCase):
    def test_validate_allows_unset_customer_name_field(self):
        settings = ZATCABusinessSettings.__new__(ZATCABusinessSettings)
        settings.customer_name_field = None
        settings.validate()

    def test_validate_allows_existing_customer_field(self):
        settings = ZATCABusinessSettings.__new__(ZATCABusinessSettings)
        settings.customer_name_field = 'customer_name'
        settings.validate()

    def test_validate_rejects_nonexistent_customer_field(self):
        settings = ZATCABusinessSettings.__new__(ZATCABusinessSettings)
        settings.customer_name_field = 'this_field_does_not_exist_on_customer'
        with self.assertRaises(frappe.ValidationError):
            settings.validate()
