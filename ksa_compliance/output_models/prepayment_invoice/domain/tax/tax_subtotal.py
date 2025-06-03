from dataclasses import dataclass
from ...validators import validate_mandatory_fields


@dataclass
class TaxSubtotal:
    taxable_amount: float
    tax_amount: float
    tax_category_id: str
    tax_percent: float
    tax_scheme: str = 'VAT'

    def __post_init__(self):
        """Validation runs automatically after initialization"""
        validate_mandatory_fields(self)
