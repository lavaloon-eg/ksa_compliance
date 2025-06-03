from dataclasses import dataclass
from ..document_reference.document_reference import DocumentReference
from ..tax.tax_total import TaxTotal
from ..item.item import Item
from ...validators import validate_mandatory_fields


@dataclass
class InvoiceLine:
    id: int
    invoice_quantity: float
    line_extension_amount: float
    uuid: str
    document_reference: DocumentReference
    tax_total: TaxTotal
    item: Item
    price: float

    def __post_init__(self):
        validate_mandatory_fields(
            self,
            {
                'id': 'Invoice line ID is mandatory',
                'uuid': 'UUID is mandatory',
                'document_reference': 'Document reference is mandatory',
                'tax_total': 'Tax total is mandatory',
            },
        )
