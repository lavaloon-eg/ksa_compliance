import frappe
from frappe import _

from dataclasses import dataclass
from typing import List, Optional

from ksa_compliance.standard_doctypes.tax_category import ZatcaTaxCategory


def validate_mandatory_fields(obj, field_rules: dict) -> None:
    """Generic mandatory field validator"""
    for field, error_msg in field_rules.items():
        if not getattr(obj, field, None):
            frappe.throw(_(error_msg))


@dataclass
class DocumentReference:
    """ZATCA-compliant document reference structure"""

    id: str
    issue_date: str
    issue_time: str
    document_type_code: str

    def __post_init__(self):
        validate_mandatory_fields(
            self,
            {
                'id': 'Document Reference ID is mandatory',
                'issue_date': 'Issue date is mandatory',
                'issue_time': 'Issue time is mandatory',
                'document_type_code': 'Document type code is mandatory',
            },
        )


@dataclass
class Item:
    name: str
    tax_category: str
    tax_percent: float
    tax_scheme: str

    def __post_init__(self):
        """Validation runs automatically after initialization"""
        validate_mandatory_fields(
            self,
            {
                'name': 'Item name is mandatory',
                'tax_category': 'Item tax category is mandatory',
                'tax_scheme': 'Item tax scheme is mandatory',
            },
        )


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
                'tax_category_id': 'Tax category ID is mandatory',
                'tax_scheme': 'Tax scheme is mandatory',
            },
        )


@dataclass
class TaxTotal:
    tax_subtotal: TaxSubtotal
    tax_amount: Optional[float] = 0.0
    rounding_amount: Optional[float] = 0.0

    def __post_init__(self):
        """Validation runs automatically after initialization"""
        validate_mandatory_fields(self, {'tax_subtotal': 'Tax subtotal is mandatory'})


@dataclass
class InvoiceLine:
    idx: int
    uuid: str
    document_reference: DocumentReference
    tax_total: TaxTotal
    item: Item
    tax_category: ZatcaTaxCategory
    invoice_quantity: Optional[float] = 0.0
    line_extension_amount: Optional[float] = 0.0
    price: Optional[float] = 0.0

    def __post_init__(self):
        validate_mandatory_fields(
            self,
            {
                'idx': 'Invoice line ID is mandatory',
                'uuid': 'UUID is mandatory',
                'document_reference': 'Document reference is mandatory',
                'tax_total': 'Tax total is mandatory',
                'item': 'Item is mandatory',
            },
        )


@dataclass
class PrepaymentInvoice:
    prepaid_amount: float
    currency: str
    invoice_lines: List[dict]
