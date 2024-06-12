from typing import NoReturn, cast, Optional, Tuple

import frappe
import frappe.utils.background_jobs
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice, make_sales_return
from result import is_ok

from ksa_compliance import logger
from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import \
    SalesInvoiceAdditionalFields, ZatcaSendMode
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings
from ksa_compliance.standard_doctypes.sales_invoice import ignore_additional_fields_for_invoice, \
    clear_additional_fields_ignore_list
from ksa_compliance.translation import ft


@frappe.whitelist()
def perform_compliance_checks(business_settings_id: str, customer_id: str, item_id: str,
                              tax_category_id: str) -> NoReturn:
    frappe.utils.background_jobs.enqueue(
        _perform_compliance_checks, business_settings_id=business_settings_id, customer_id=customer_id, item_id=item_id,
        tax_category_id=tax_category_id)


def _perform_compliance_checks(business_settings_id: str, customer_id: str, item_id: str,
                               tax_category_id: str) -> NoReturn:
    def progress(description: str, percent: float) -> None:
        logger.info(f"[Compliance Check] {description} ({percent}%)")
        frappe.publish_progress(title=ft('Compliance Check'), description=description, percent=percent)

    try:
        settings = cast(ZATCABusinessSettings, frappe.get_doc('ZATCA Business Settings', business_settings_id))

        progress(ft('Creating simplified invoice'), 0.0)
        invoice = make_invoice(settings.company, customer_id, item_id, tax_category_id)
        invoice.save()

        progress(ft('Submitting simplified invoice'), 11.0)
        ignore_additional_fields_for_invoice(invoice.name)
        invoice.submit()

        progress(ft('Checking simplified invoice compliance'), 22.0)
        result, details = check_invoice_compliance(invoice)

        # We need to check the credit note and debit note separately, so we roll back to this save point after checking
        # the credit note. Otherwise, the debit note ends up with 0 qty for the item (since the credit note returns it)
        frappe.db.savepoint('before_credit_note')

        progress(ft('Creating simplified credit note'), 33.0)
        return_invoice = cast(SalesInvoice, make_sales_return(invoice.name))
        return_invoice.custom_return_reason = 'Goods returned'
        return_invoice.set_taxes()
        return_invoice.set_missing_values()
        return_invoice.save()

        progress(ft('Submitting simplified credit note'), 44.0)
        ignore_additional_fields_for_invoice(return_invoice.name)
        return_invoice.submit()

        progress(ft('Checking simplified credit note compliance'), 55.0)
        credit_note_result, credit_note_details = check_invoice_compliance(return_invoice)

        frappe.db.rollback(save_point='before_credit_note')
        progress(ft('Creating simplified debit note'), 66.0)
        debit_invoice = cast(SalesInvoice, make_sales_return(invoice.name))
        debit_invoice.custom_return_reason = 'Goods returned'
        debit_invoice.is_debit_note = True
        debit_invoice.set_taxes()
        debit_invoice.set_missing_values()
        debit_invoice.save()

        progress(ft('Submitting simplified debit note'), 77.0)
        ignore_additional_fields_for_invoice(debit_invoice.name)
        debit_invoice.submit()

        progress(ft('Checking simplified debit note compliance'), 88.0)
        debit_note_result, debit_note_details = check_invoice_compliance(debit_invoice)

        progress(ft('Done'), 100)

        error_log = frappe.log_error(title='Compliance Check Result',
                                     message=f"Simplified Invoice Result: {result}\n"
                                             f"{details}\n"
                                             f"Simplified Credit Note Result: {credit_note_result}\n"
                                             f"{credit_note_details}\n"
                                             f"Simplified Debit Note Result: {debit_note_result}\n"
                                             f"{debit_note_details}\n")

        # Submitting the above invoices results in a number of messages about payment reconciliation and the like,
        # and we don't to show those with the result of the compliance check
        frappe.clear_messages()

        error_link = frappe.utils.get_link_to_form('Error Log', error_log.name)
        frappe.msgprint(f"""
    <ul>
    <li>Simplified invoice result: {result}</li>
    <li>Simplified credit note result: {credit_note_result}</li>
    <li>Simplified debit note result: {debit_note_result}</li>
    </ul>
    <p>Please check Error Log {error_link} for ZATCA responses</p>
    """, realtime=True)
    finally:
        clear_additional_fields_ignore_list()
        logger.info("Rolling back")
        frappe.db.rollback()


def make_invoice(company: str, customer: str, item: str, tax_category_id: str) -> SalesInvoice:
    invoice = cast(SalesInvoice, frappe.new_doc('Sales Invoice'))
    invoice.company = company
    invoice.customer = customer
    invoice.tax_category = tax_category_id
    invoice.set_taxes()
    invoice.append('items', {'item_code': item, 'qty': 1.0})
    invoice.set_missing_values()
    invoice.save()
    return invoice


def check_invoice_compliance(invoice: SalesInvoice) -> Tuple[str, Optional[str]]:
    si_additional_fields_doc = cast(SalesInvoiceAdditionalFields, frappe.new_doc("Sales Invoice Additional Fields"))
    si_additional_fields_doc.send_mode = ZatcaSendMode.Compliance
    si_additional_fields_doc.sales_invoice = invoice.name
    si_additional_fields_doc.flags.ignore_permissions = True
    si_additional_fields_doc.insert()
    result = si_additional_fields_doc.submit_to_zatca()
    if is_ok(result):
        zatca_message = frappe.get_value('ZATCA Integration Log',
                                         {'invoice_additional_fields_reference': si_additional_fields_doc.name},
                                         ['zatca_message'])
        return result.ok_value, zatca_message

    return result.err_value, None
