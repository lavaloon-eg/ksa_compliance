from enum import Enum
from typing import Literal


class InvoiceMode(Enum):
    Auto = 'Let the system decide (both)'
    Simplified = 'Simplified Tax Invoices'
    Standard = 'Standard Tax Invoices'

    @staticmethod
    def from_literal(mode: str) -> 'InvoiceMode':
        for value in InvoiceMode:
            if value.value == mode:
                return value
        raise ValueError(f'Unknown value: {mode}')


InvoiceType = Literal['Standard', 'Simplified']
