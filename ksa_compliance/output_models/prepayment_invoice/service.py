from frappe import _
import frappe

from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice


def update_result(result: dict, doc: SalesInvoice) -> None:
    prepaid_amount = 0
    for row in result['prepayment_invoice']['invoice_lines']:
        prepaid_amount += (
            row['tax_total']['tax_sub_total']['taxable_amount'] + row['tax_total']['tax_sub_total']['tax_amount']
        )
    result['prepayment_invoice']['prepaid_amount'] = prepaid_amount
    result['invoice']['payable_amount'] = (
        result['invoice']['payable_amount'] - result['prepayment_invoice']['prepaid_amount']
    )


def validate_prepayment_invoice_is_sent(doc: SalesInvoice) -> None:
    advances = frappe.db.get_all(
        'Sales Invoice Advance',
        filters={'parent': doc.name},
        fields=['reference_type', 'reference_name', 'custom_prepayment_invoice'],
        order_by='idx',
    )
    for advance in advances:
        if not advance.custom_prepayment_invoice:
            frappe.throw(
                _('Prepayment Invoice is not sent for {0} {1}').format(advance.reference_type, advance.reference_name),
            )
