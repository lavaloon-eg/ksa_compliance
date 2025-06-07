import frappe
from typing import Literal
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from dataclasses import asdict, is_dataclass


def dataclass_to_frappe_dict(obj) -> frappe._dict:
    if is_dataclass(obj):
        obj = asdict(obj)

    if isinstance(obj, dict):
        return frappe._dict({k: dataclass_to_frappe_dict(v) for k, v in obj.items()})

    if isinstance(obj, list):
        return [dataclass_to_frappe_dict(v) for v in obj]

    return obj


def get_right_fieldname(field_name: str, source_doc: Literal['Sales Invoice', 'Payment Entry']):
    """
    This method is used to get the right field name and value from the source document.
    """
    pe_field_map = {
        'grand_total': 'received_amount_after_tax',
        'included_in_print_rate': 'included_in_paid_amount',
        'taxes_and_charges': 'sales_taxes_and_charges_template',
        'net_total': 'received_amount',
        'posting_time': 'custom_posting_time',
        'currency': 'paid_from_account_currency',
        'tax_currency': 'paid_from_account_currency',
        'customer_name': 'party_name',
    }
    if source_doc == 'Payment Entry':
        if field_name in pe_field_map:
            field_name = pe_field_map[field_name]
    return field_name


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
