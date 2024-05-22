import json
from json import JSONDecodeError

import frappe
from typing import NoReturn, cast

from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice, make_sales_return

from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import \
    SalesInvoiceAdditionalFields, ZatcaSendMode
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings
from ksa_compliance import logger
from ksa_compliance.standard_doctypes.sales_invoice import ignore_additional_fields_for_invoice, \
    clear_additional_fields_ignore_list


@frappe.whitelist()
def perform_compliance_checks(business_settings_id: str, customer_id: str, item_id: str) -> NoReturn:
    try:
        settings = cast(ZATCABusinessSettings, frappe.get_doc('ZATCA Business Settings', business_settings_id))

        logger.info("Checking simplified invoice compliance")
        invoice = make_invoice(settings.company, customer_id, item_id)
        ignore_additional_fields_for_invoice(invoice.name)
        invoice.submit()
        result = check_invoice_compliance(settings, invoice)

        logger.info("Checking credit note compliance")
        return_invoice = cast(SalesInvoice, make_sales_return(invoice.name))
        return_invoice.custom_return_reason = 'Goods returned'
        return_invoice.set_taxes()
        return_invoice.set_missing_values()
        return_invoice.save()
        credit_note_result = check_invoice_compliance(settings, return_invoice)

        logger.info("Checking debit note compliance")
        debit_invoice = cast(SalesInvoice, make_sales_return(invoice.name))
        debit_invoice.custom_return_reason = 'Goods returned'
        debit_invoice.is_debit_note = True
        debit_invoice.set_taxes()
        debit_invoice.set_missing_values()
        debit_invoice.save()
        debit_invoice.save()
        debit_note_result = check_invoice_compliance(settings, debit_invoice)

        frappe.msgprint(f"""<ul>
        <li>Simplified Invoice Result: {result}</li>
        <li>Simplified Credit Note Result: {credit_note_result}</li>
        <li>Simplified Debit Note Result: {debit_note_result}</li>
        """)
    finally:
        clear_additional_fields_ignore_list()
        logger.info("Rolling back")
        frappe.db.rollback()


def make_invoice(company: str, customer: str, item: str) -> SalesInvoice:
    invoice = cast(SalesInvoice, frappe.new_doc('Sales Invoice'))
    invoice.company = company
    invoice.customer = customer
    invoice.set_taxes()
    invoice.append('items', {'item_code': item, 'qty': 1.0})
    invoice.set_missing_values()
    invoice.save()
    return invoice


def check_invoice_compliance(settings: ZATCABusinessSettings, invoice: SalesInvoice) -> str:
    si_additional_fields_doc = cast(SalesInvoiceAdditionalFields, frappe.new_doc("Sales Invoice Additional Fields"))
    si_additional_fields_doc.send_mode = ZatcaSendMode.Compliance
    si_additional_fields_doc.sales_invoice = invoice.name
    si_additional_fields_doc.insert()
    response = si_additional_fields_doc.send_to_zatca(settings)
    logger.info(response)
    try:
        data = json.loads(response)
        return data.get('status')
    except JSONDecodeError:
        return response
