from ksa_compliance.tests.case import ZatcaTestCase
from ksa_compliance.tests.invoice_xml import InvoiceXml


class TestBrCo15(ZatcaTestCase):
    """BR-CO-15: invoice total with VAT (BT-112) = total without VAT (BT-109) + total VAT (BT-110).

    BT-110 is checked both as written in ``cac:TaxTotal`` and as the sum of the VAT breakdown, which is
    the reading that matched ZATCA's verdict on every rejected production invoice.
    """

    def test_total_with_vat_adds_up(self):
        def check(xml: InvoiceXml):
            self.assertEqual(xml.bt112, xml.bt109 + xml.bt110, 'BT-110 read from cac:TaxTotal')
            self.assertEqual(xml.bt112, xml.bt109 + xml.sum_bt117, 'BT-110 read from the VAT breakdown')

        self.assert_each_scenario(check)
