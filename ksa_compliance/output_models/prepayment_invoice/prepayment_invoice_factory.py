import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

from dataclasses import asdict

from .invoice_line_factory import invoice_line_create
from .models import PrepaymentInvoice


def prepayment_invoice_factory_create(doc: SalesInvoice) -> PrepaymentInvoice:
    prepayment_invoice = PrepaymentInvoice(
        prepaid_amount=_get_prepaid_amount(doc),
        currency=doc.currency,
        invoice_lines=invoice_line_create(doc),
    )
    return asdict(prepayment_invoice)


def _get_prepaid_amount(doc: SalesInvoice) -> float:
    prepaid_amount = 0
    for row in doc.advances:
        if frappe.db.get_value('Payment Entry', row.reference_name, 'custom_prepayment_invoice'):
            tax_amount = frappe.db.get_value(
                row.reference_type,
                row.reference_name,
                'total_taxes_and_charges',
            )
            prepaid_amount += row.allocated_amount + tax_amount
    return abs(prepaid_amount) if prepaid_amount else 0.0
