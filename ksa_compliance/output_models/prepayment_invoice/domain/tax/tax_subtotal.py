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
        validate_mandatory_fields(
            self,
            {
                'taxable_amount': 'Taxable amount is mandatory',
                'tax_amount': 'Tax amount is mandatory',
                'tax_category_id': 'Tax category ID is mandatory',
                'tax_percent': 'Tax percent is mandatory',
            },
        )
