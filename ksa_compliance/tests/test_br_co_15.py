from ksa_compliance.tests.case import ZatcaTestCase
from ksa_compliance.tests.invoice_xml import InvoiceXml


class TestBrCo15(ZatcaTestCase):
    """BR-CO-15: invoice total with VAT (BT-112) = total without VAT (BT-109) + total VAT (BT-110)."""

    def test_total_with_vat_adds_up(self):
        def check(xml: InvoiceXml):
            self.assertEqual(
                xml.bt112_tax_inclusive_amount,
                xml.bt109_tax_exclusive_amount + xml.bt110_total_vat_amount,
                'BT-110 read from cac:TaxTotal',
            )

        self.assert_each_scenario(check)
