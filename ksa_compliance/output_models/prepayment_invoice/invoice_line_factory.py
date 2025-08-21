import frappe
from dataclasses import asdict
from datetime import timedelta

from .models import DocumentReference, Item, InvoiceLine, TaxSubtotal, TaxTotal
from ksa_compliance.standard_doctypes.tax_category import map_tax_category
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
from erpnext.accounts.doctype.sales_invoice_payment.sales_invoice_payment import SalesInvoicePayment

from ksa_compliance import PREPAYMENT_INVOICE_CODE
from typing import cast


def invoice_line_create(doc: SalesInvoice) -> list[dict]:
    """Create invoice lines from document advances"""
    return [
        asdict(_create_invoice_line(advance, doc))
        for advance in doc.advances
        if frappe.db.get_value('Payment Entry', advance.reference_name, 'custom_prepayment_invoice')
    ]


def _create_invoice_line(advance: SalesInvoicePayment, doc: SalesInvoice) -> InvoiceLine:
    ref_doc = cast(PaymentEntry, frappe.get_cached_doc(advance.reference_type, advance.reference_name))

    tax_percent, tax_category_id = _get_tax_info(ref_doc)
    tax_category = map_tax_category(tax_category_id=tax_category_id)
    taxable_amount = abs(advance.allocated_amount) / (1 + (tax_percent / 100))
    tax_amount = abs(advance.allocated_amount) - taxable_amount
    return InvoiceLine(
        idx=advance.idx
        + len(
            doc.items
        ),  # Ensure unique ID by offsetting with number of items also zatca refused advance.reference_name as id here
        invoice_quantity=0.0,
        line_extension_amount=0.0,
        uuid=_get_uuid(ref_doc),
        document_reference=DocumentReference(
            id=advance.reference_name,
            document_type_code=PREPAYMENT_INVOICE_CODE,
            issue_date=ref_doc.posting_date.strftime('%Y-%m-%d'),
            issue_time=_format_time(ref_doc.custom_posting_time),
        ),
        tax_total=TaxTotal(
            tax_amount=0.0,
            rounding_amount=0.0,
            tax_subtotal=TaxSubtotal(
                taxable_amount=taxable_amount,
                tax_amount=abs(tax_amount),
                tax_category_id=tax_category.tax_category_code,
                tax_percent=tax_percent,
            ),
        ),
        item=Item(
            name=ref_doc.custom_prepayment_invoice_description,
            tax_category=tax_category.tax_category_code,
            tax_percent=tax_percent,
            tax_scheme='VAT',
        ),
        tax_category=tax_category,
        price=0.0,
    )


def _get_uuid(document_reference: PaymentEntry) -> str:
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


def _get_tax_info(document_reference: PaymentEntry) -> tuple[float, str]:
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
