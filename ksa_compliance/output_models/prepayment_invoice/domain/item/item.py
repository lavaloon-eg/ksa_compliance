from dataclasses import dataclass
from ...validators import validate_mandatory_fields


@dataclass
class Item:
    name: str
    item_tax_category: str
    item_tax_percent: float
    item_tax_scheme: str

    def __post_init__(self):
        """Validation runs automatically after initialization"""
        validate_mandatory_fields(
            self,
            {
                'name': 'Item name is mandatory',
                'item_tax_category': 'Item tax category is mandatory',
                'item_tax_percent': 'Item tax percent is mandatory',
                'item_tax_scheme': 'Item tax scheme is mandatory',
            },
        )
