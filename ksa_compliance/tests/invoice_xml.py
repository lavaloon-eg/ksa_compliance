import xml.etree.ElementTree as Et
from decimal import Decimal
from typing import NamedTuple

NAMESPACES = {
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
}


class VatBreakdown(NamedTuple):
    """The amounts ZATCA's business rules compare, read from a generated invoice XML as exact decimals.

    The rules compare two-decimal amounts for exact equality, and a float sum
    such as 62.70 + 9.40 = 72.10000000000001 would fail a comparison the XML actually satisfies.
    """

    category: str
    """BT-118"""
    rate: Decimal
    """BT-119"""
    taxable_amount: Decimal
    """BT-116"""
    tax_amount: Decimal
    """BT-117"""


class InvoiceXml:
    def __init__(self, xml: str):
        self.tree = Et.fromstring(xml)

    def _amount(self, path: str, element: Et.Element | None = None) -> Decimal:
        return Decimal((self.tree if element is None else element).findtext(path, namespaces=NAMESPACES))

    @property
    def bt109_tax_exclusive_amount(self) -> Decimal:
        """Invoice total amount without VAT."""
        return self._amount('cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount')

    @property
    def bt110_total_vat_amount(self) -> Decimal:
        """Invoice total VAT amount."""
        return self._amount('cac:TaxTotal[cac:TaxSubtotal]/cbc:TaxAmount')

    @property
    def bt112_tax_inclusive_amount(self) -> Decimal:
        """Invoice total amount with VAT."""
        return self._amount('cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount')

    @property
    def vat_breakdown(self) -> list[VatBreakdown]:
        """One entry per VAT category (BG-23)."""
        return [
            VatBreakdown(
                category=subtotal.findtext('cac:TaxCategory/cbc:ID', namespaces=NAMESPACES),
                rate=self._amount('cac:TaxCategory/cbc:Percent', subtotal),
                taxable_amount=self._amount('cbc:TaxableAmount', subtotal),
                tax_amount=self._amount('cbc:TaxAmount', subtotal),
            )
            for subtotal in self.tree.iterfind('cac:TaxTotal/cac:TaxSubtotal', NAMESPACES)
        ]

    @property
    def sum_bt117_tax_subtotals(self) -> Decimal:
        """Sum of the VAT category tax amounts in the VAT breakdown (BG-23)."""
        return sum((row.tax_amount for row in self.vat_breakdown), Decimal(0))

    @property
    def line_vat(self) -> list[Decimal]:
        """The VAT amount of each invoice line (KSA-11), each rounded on its own."""
        return [
            self._amount('cac:TaxTotal/cbc:TaxAmount', line)
            for line in self.tree.iterfind('cac:InvoiceLine', NAMESPACES)
        ]

    @property
    def sum_line_vat(self) -> Decimal:
        """Sum of the per-line VAT amounts, the total that drifts from the invoice VAT."""
        return sum(self.line_vat, Decimal(0))
