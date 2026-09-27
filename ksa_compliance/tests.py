from frappe import __version__ as frappe_version

FrappeTestCaseClass = None
if frappe_version >= '16.0.0':
    from frappe.tests import IntegrationTestCase

    FrappeTestCaseClass = IntegrationTestCase
else:
    from frappe.tests.utils import FrappeTestCase

    FrappeTestCaseClass = FrappeTestCase
