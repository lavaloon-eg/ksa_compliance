try:
    from frappe.tests import IntegrationTestCase as FrappeTestCaseClass
    from frappe.tests.classes.context_managers import change_settings
except ImportError:  # Frappe v15
    from frappe.tests.utils import FrappeTestCase as FrappeTestCaseClass
    from frappe.tests.utils import change_settings

__all__ = ['FrappeTestCaseClass', 'change_settings']
