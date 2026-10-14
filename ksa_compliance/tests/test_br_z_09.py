from ksa_compliance.tests.case import ZatcaTestCase
from ksa_compliance.tests.scenarios import ZERO_RATED


class TestBrZ09(ZatcaTestCase):
    """BR-Z-09: the VAT category tax amount (BT-117) of the 'Zero rated' category (Z) is 0."""

    def test_category_carries_no_vat(self):
        self.assert_category_carries_no_vat(ZERO_RATED)
