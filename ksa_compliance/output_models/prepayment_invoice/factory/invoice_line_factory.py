import frappe
from dataclasses import asdict
from datetime import timedelta

from ..domain.prepayment_invoice_line.prepayment_invoice_line import InvoiceLine
from ..domain.document_reference.document_reference import DocumentReference
from ..domain.tax.tax_total import TaxTotal
from ..domain.tax.tax_subtotal import TaxSubtotal
from ..domain.item.item import Item
from ksa_compliance.standard_doctypes.tax_category import map_tax_category


def invoice_line_create(doc) -> list[dict]:
    """Create invoice lines from document advances"""
    return [asdict(_create_invoice_line(advance, doc)) for advance in doc.advances]


def _create_invoice_line(advance, doc) -> InvoiceLine:
    ref_doc = frappe.get_cached_doc(advance.reference_type, advance.reference_name)

    tax_percent, tax_category_id = _get_tax_info(ref_doc)
    tax_category = map_tax_category(tax_category_id=tax_category_id)

    return InvoiceLine(
        id=advance.reference_name,
        invoice_quantity=0.0,
        line_extension_amount=0.0,
        uuid=_get_uuid(advance, ref_doc),
        document_reference=DocumentReference(
            id=advance.reference_name,
            issue_date=ref_doc.posting_date.strftime('%Y-%m-%d'),
            issue_time=_format_time(ref_doc.custom_posting_time),
        ),
        tax_total=TaxTotal(
            tax_amount=0.0,
            rounding_amount=0.0,
            tax_subtotal=TaxSubtotal(
                taxable_amount=advance.allocated_amount,
                tax_amount=advance.allocated_amount * (tax_percent / 100),
                tax_category_id=tax_category.tax_category_code,
                tax_percent=tax_percent,
            ),
        ),
        item=Item(
            name=ref_doc.custom_prepayment_invoice_description,
            item_tax_category=tax_category.tax_category_code,
            item_tax_percent=tax_percent,
        ),
        price=0.0,
    )


# Helper Functions
def _get_uuid(advance, document_reference) -> str:
    return frappe.db.get_value(
        'Sales Invoice Additional Fields',
        {'invoice_doctype': document_reference.doctype, 'sales_invoice': document_reference.name},
        'uuid',
    )


def _format_time(time_delta: timedelta) -> str:
    """Convert timedelta to HH:MM:SS format"""
    total_seconds = time_delta.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    return f'{hours:02d}:{minutes:02d}:00'


def _get_tax_info(document_reference) -> tuple[float, str]:
    """Get tax percent and category from document"""
    tax_percent = frappe.db.get_value(
        'Sales Taxes and Charges',
        {
            'parent': document_reference.sales_taxes_and_charges_template,
            'parenttype': 'Sales Taxes and Charges Template',
        },
        'rate',
    )
    tax_id = frappe.db.get_value(
        'Sales Taxes and Charges Template', document_reference.sales_taxes_and_charges_template, 'tax_category'
    )
    return tax_percent, tax_id
