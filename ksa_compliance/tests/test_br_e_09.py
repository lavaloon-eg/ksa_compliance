from ksa_compliance.tests.case import ZatcaTestCase
from ksa_compliance.tests.scenarios import EXEMPT


class TestBrE09(ZatcaTestCase):
    """BR-E-09: the VAT category tax amount (BT-117) of the 'Exempt from VAT' category (E) is 0."""

    def test_category_carries_no_vat(self):
        self.assert_category_carries_no_vat(EXEMPT)
