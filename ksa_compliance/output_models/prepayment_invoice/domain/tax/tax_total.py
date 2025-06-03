from dataclasses import dataclass
from .tax_subtotal import TaxSubtotal
from ...validators import validate_mandatory_fields


@dataclass
class TaxTotal:
    tax_amount: float
    rounding_amount: float
    tax_subtotal: TaxSubtotal

    def __post_init__(self):
        """Validation runs automatically after initialization"""
        validate_mandatory_fields(self, {'tax_subtotal': 'Tax subtotal is mandatory'})
