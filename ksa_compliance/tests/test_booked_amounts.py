from decimal import Decimal

from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

from ksa_compliance.tests.case import ZatcaTestCase
from ksa_compliance.tests.invoice_xml import InvoiceXml
from ksa_compliance.tests.scenarios import Scenario


def booked(amount: float) -> Decimal:
    """An amount as ERPNext books it, unsigned the way the XML reports credit notes."""
    return Decimal(str(abs(amount or 0))).quantize(Decimal('0.01'))


class TestBookedAmounts(ZatcaTestCase):
    """Not a ZATCA rule: the XML reports the VAT ERPNext books, so fixing the VAT breakdown moves no money."""

    def test_invoice_vat_is_the_booked_vat(self):
        self.for_each_scenario(
            lambda scenario, invoice, xml: self.assertEqual(xml.bt110, booked(invoice.total_taxes_and_charges))
        )

    def test_line_vat_is_the_booked_line_vat(self):
        def check(scenario: Scenario, invoice: SalesInvoice, xml: InvoiceXml):
            self.assertEqual(xml.line_vat, [booked(item.tax_amount) for item in invoice.items])

        self.for_each_scenario(check)
