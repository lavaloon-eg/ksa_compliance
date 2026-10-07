"""The base class of the ZATCA rule tests: it turns each scenario into the XML ZATCA would receive.

Test data is created once per test class and rolled back when the class finishes.
"""

from collections.abc import Callable, Iterable
from unittest.mock import patch

from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

from ksa_compliance.generate_xml import generate_xml_file
from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import (
    SalesInvoiceAdditionalFields,
)
from ksa_compliance.output_models.e_invoice_output_model import Einvoice
from ksa_compliance.tests import FrappeTestCaseClass, change_settings
from ksa_compliance.tests.fixtures import make_invoice, make_test_data
from ksa_compliance.tests.invoice_xml import InvoiceXml
from ksa_compliance.tests.scenarios import ROUNDING_METHOD, SCENARIOS, Scenario, scenarios_with


class ZatcaTestCase(FrappeTestCaseClass):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tax_templates = make_test_data()
        # Pinned after the test data: creating a company can run DDL, which commits the transaction.
        rounding = change_settings('System Settings', rounding_method=ROUNDING_METHOD)
        rounding.__enter__()
        cls.addClassCleanup(rounding.__exit__, None, None, None)

    def for_each_scenario(
        self,
        check: Callable[[Scenario, SalesInvoice, InvoiceXml], None],
        scenarios: Iterable[Scenario] = SCENARIOS,
    ):
        """Bill each scenario and run ``check`` on the invoice and its XML, as a subtest per scenario."""
        for scenario in scenarios:
            with self.subTest(scenario=scenario.name):
                invoice = make_invoice(scenario, self.tax_templates)
                check(scenario, invoice, InvoiceXml(build_invoice_xml(invoice)))

    def assert_each_scenario(self, check: Callable[[InvoiceXml], None], scenarios: Iterable[Scenario] = SCENARIOS):
        """``for_each_scenario`` for checks that only need the XML."""
        self.for_each_scenario(lambda scenario, invoice, xml: check(xml), scenarios)

    def assert_category_carries_no_vat(self, category: str):
        def check(xml: InvoiceXml):
            rows = [row for row in xml.vat_breakdown if row.category == category]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].rate, 0)
            self.assertEqual(rows[0].tax_amount, 0)

        scenarios = scenarios_with(category)
        self.assertTrue(scenarios, f'No scenario has a {category} line')
        self.assert_each_scenario(check, scenarios)


def build_invoice_xml(invoice: SalesInvoice) -> str:
    """Prepare the invoice for ZATCA exactly as submitting it does, stopping before it is signed."""
    xml = []

    def render(siaf, settings, invoice_type):
        xml.append(
            generate_xml_file(Einvoice(sales_invoice_additional_fields_doc=siaf, invoice_type=invoice_type).result)
        )

    siaf = SalesInvoiceAdditionalFields.create_for_invoice(invoice.name, invoice.doctype)
    with patch.object(SalesInvoiceAdditionalFields, '_prepare_for_zatca', render):
        siaf.before_insert()
    return xml[0]
