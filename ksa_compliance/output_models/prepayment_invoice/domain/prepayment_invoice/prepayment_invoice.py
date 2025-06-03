from dataclasses import dataclass
from typing import List
from ...validators import validate_mandatory_fields


@dataclass
class PrepaymentInvoice:
    prepaid_amount: float
    currency: str
    invoice_lines: List[dict]
    uuid: str

    def __post_init__(self):
        """Validation runs automatically after initialization"""
        validate_mandatory_fields(
            self,
            {
                'prepaid_amount': 'Prepaid amount is mandatory',
                'invoice_lines': 'Invoice lines are mandatory',
                'uuid': 'UUID is mandatory',
            },
        )
