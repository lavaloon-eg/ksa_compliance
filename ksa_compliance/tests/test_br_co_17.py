from decimal import ROUND_HALF_UP, Decimal

from ksa_compliance.tests.case import ZatcaTestCase
from ksa_compliance.tests.invoice_xml import InvoiceXml

HALALA = Decimal('0.01')


class TestBrCo17(ZatcaTestCase):
    """BR-CO-17: VAT category tax amount (BT-117) = taxable amount (BT-116) x rate (BT-119) / 100, rounded to 2 decimals.

    One halala of difference is allowed: the category VAT follows the VAT ERPNext books for the invoice, which is
    rounded once for the whole invoice rather than from the category's rounded taxable amount.
    """

    def test_category_vat_matches_its_taxable_amount(self):
        def check(xml: InvoiceXml):
            for row in xml.vat_breakdown:
                expected = (row.taxable_amount * row.rate / 100).quantize(HALALA, ROUND_HALF_UP)
                self.assertLessEqual(abs(row.tax_amount - expected), HALALA, row)

        self.assert_each_scenario(check)
