from ksa_compliance.tests.case import ZatcaTestCase


class TestBrCo14(ZatcaTestCase):
    """BR-CO-14: invoice total VAT amount (BT-110) = sum of VAT category tax amounts (BT-117)."""

    def test_vat_breakdown_adds_up_to_invoice_vat(self):
        self.assert_each_scenario(lambda xml: self.assertEqual(xml.bt110, xml.sum_bt117))
