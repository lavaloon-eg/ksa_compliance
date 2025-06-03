import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

from dataclasses import asdict

from .invoice_line_factory import invoice_line_create
from ..domain.prepayment_invoice.prepayment_invoice import PrepaymentInvoice


def prepayment_invoice_factory_create(zatca_fields_dto: dict, doc: SalesInvoice) -> PrepaymentInvoice:
    prepayment_invoice = PrepaymentInvoice(
        prepaid_amount=_get_prepaid_amount(doc),
        currency=_get_currency(doc),
        invoice_lines=_get_invoice_lines(zatca_fields_dto, doc),
    )
    return asdict(prepayment_invoice)


def _get_invoice_lines(zatca_fields_dto: dict, doc: SalesInvoice):
    invoicelines = invoice_line_create(zatca_fields_dto, doc)
    return invoicelines


def _get_prepaid_amount(doc: SalesInvoice) -> float:
    prepaid_amount = 0
    for row in doc.advances:
        tax_amount = frappe.db.get_value(
            row.reference_type,
            row.reference_name,
            'total_taxes_and_charges',
        )
        prepaid_amount += row.allocated_amount + tax_amount
    return prepaid_amount if prepaid_amount else 0.0


def _get_currency(doc: SalesInvoice) -> str:
    return doc.currency
