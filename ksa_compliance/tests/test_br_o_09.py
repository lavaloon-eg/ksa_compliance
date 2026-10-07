from ksa_compliance.tests.case import ZatcaTestCase
from ksa_compliance.tests.scenarios import OUT_OF_SCOPE


class TestBrO09(ZatcaTestCase):
    """BR-O-09: the VAT category tax amount (BT-117) of the 'Not subject to VAT' category (O) is 0."""

    def test_category_carries_no_vat(self):
        self.assert_category_carries_no_vat(OUT_OF_SCOPE)
