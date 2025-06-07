from dataclasses import dataclass
from typing import Optional, List
from erpnext.stock.doctype.item.item import Item


@dataclass
class ZatcaTaxCategory:
    """Holds ZATCA tax category code, reason and reason code"""

    tax_category_code: str = None
    reason_code: Optional[str] = None
    arabic_reason: Optional[str] = None


@dataclass
class TaxCategory:
    id: ZatcaTaxCategory
    percent: int
    tax_scheme_id: str = 'VAT'


@dataclass
class TaxCategoryByItems:
    tax_category: TaxCategory
    items: List[Item]


@dataclass
class AllowanceCharge:
    tax_category: TaxCategory
    amount: float = 0.0
    charge_indicator: str = 'fales'
    allowance_charge_reason: str = 'discount'


@dataclass
class TaxSubtotal:
    taxable_amount: float
    tax_amount: float
    tax_category: TaxCategory


@dataclass
class TaxTotal:
    tax_amount: float
    taxable_amount: float
    tax_subtotal: List[TaxSubtotal]
