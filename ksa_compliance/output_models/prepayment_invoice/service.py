from frappe import _
import frappe

from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice


def update_result(result: dict, doc: SalesInvoice) -> None:
    prepaid_amount = 0
    for row in result['prepayment_invoice']['invoice_lines']:
        prepaid_amount += (
            row['tax_total']['tax_subtotal']['taxable_amount'] + row['tax_total']['tax_subtotal']['tax_amount']
        )
    result['prepayment_invoice']['prepaid_amount'] = prepaid_amount
    result['invoice']['payable_amount'] = (
        result['invoice']['payable_amount'] - result['prepayment_invoice']['prepaid_amount']
    )


def validate_prepayment_invoice_is_sent(doc: SalesInvoice) -> None:
    SalesInvoiceAdvance = frappe.qb.DocType('Sales Invoice Advance')
    PaymentEntry = frappe.qb.DocType('Payment Entry')
    advances = (
        frappe.qb.from_(SalesInvoiceAdvance)
        .select(
            SalesInvoiceAdvance.reference_type,
            SalesInvoiceAdvance.reference_name,
            PaymentEntry.custom_prepayment_invoice,
        )
        .where((SalesInvoiceAdvance.parent == doc.name))
        .where(SalesInvoiceAdvance.reference_type == 'Payment Entry')
        .inner_join(PaymentEntry)
        .on(SalesInvoiceAdvance.reference_name == PaymentEntry.name)
        .where(PaymentEntry.docstatus == 1)
        .where(PaymentEntry.custom_prepayment_invoice == 0)
    ).run(as_dict=True)
    if advances:
        frappe.throw(
            _('Prepayment Invoice is not sent for {0}').format(
                ', '.join([advance['reference_name'] for advance in advances])
            ),
            title=_('Prepayment Invoice Not Sent'),
        )
