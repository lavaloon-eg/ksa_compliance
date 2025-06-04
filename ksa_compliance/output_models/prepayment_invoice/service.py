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
