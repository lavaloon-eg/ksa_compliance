from dataclasses import dataclass
from typing import NoReturn, cast, Optional, Tuple

import frappe
import frappe.utils.background_jobs
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice, make_sales_return
from frappe.model.document import Document
from result import is_ok

from ksa_compliance import logger
from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import (
    SalesInvoiceAdditionalFields,
    ZatcaSendMode,
)
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings
from ksa_compliance.standard_doctypes.sales_invoice import (
    ignore_additional_fields_for_invoice,
    clear_additional_fields_ignore_list,
)
from ksa_compliance.translation import ft


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def customer_query(
    doctype: str, txt: Optional[str], searchfield: str, start: int, page_len: int, filters: dict
) -> list:
    search_text = f'%{txt}%'
    if filters.get('standard'):
        # For standard (B2B) customers, we want customers who either have a VAT registration number or another ID
        # defined in the additional IDs table. We want to return the VAT or ID formatted in the form: "Code: ..."
        # e.g. "VAT: 12345666" or "CRN: 12345666"
        # Note that we select one ID only, so we go through them in priority order (as defined by idx)
        return frappe.db.sql(
            f"""
SELECT name, customer_name, IFNULL(custom_vat_registration_number, other_id)
FROM (SELECT c.name,
             c.customer_name,
             IF(c.custom_vat_registration_number = '', NULL,
                CONCAT('VAT: ', c.custom_vat_registration_number)) AS custom_vat_registration_number,
             (SELECT CONCAT(ids.type_code, ': ', ids.value)
              FROM `tabAdditional Buyer IDs` ids
              WHERE ids.parent = c.name
                AND ids.value IS NOT NULL
                AND ids.value != ''
              ORDER BY ids.idx
              LIMIT 1) AS other_id
      FROM tabCustomer c
      WHERE (%(txt)s = '' OR {searchfield} LIKE %(txt)s)
      ORDER BY modified DESC
      ) customers
WHERE IFNULL(custom_vat_registration_number, '') != '' OR other_id IS NOT NULL
LIMIT %(page_len)s OFFSET %(start)s
""",
            {'txt': search_text, 'page_len': page_len, 'start': start},
        )

    return frappe.db.sql(
        f"SELECT c.name, c.customer_name FROM tabCustomer c WHERE (%(txt)s = '' OR c.{searchfield} LIKE %(txt)s)"
        " AND IFNULL(custom_vat_registration_number, '') = '' AND"
        ' NOT EXISTS (SELECT 1 FROM `tabAdditional Buyer IDs` ids WHERE ids.parent = c.name AND ids.value IS NOT NULL'
        " AND ids.value != '')"
        ' ORDER BY modified DESC LIMIT %(page_len)s OFFSET %(start)s ',
        {'txt': search_text, 'page_len': page_len, 'start': start},
    )


@frappe.whitelist()
def perform_compliance_checks(
    business_settings_id: str,
    simplified_customer_id: Optional[str],
    standard_customer_id: Optional[str],
    item_id: str,
    tax_category_id: str,
) -> NoReturn:
    frappe.utils.background_jobs.enqueue(
        _perform_compliance_checks,
        business_settings_id=business_settings_id,
        simplified_customer_id=simplified_customer_id,
        standard_customer_id=standard_customer_id,
        item_id=item_id,
        tax_category_id=tax_category_id,
    )


@dataclass
class _ComplianceResult:
    invoice_result: str
    invoice_details: Optional[str]
    credit_note_result: str
    credit_note_details: Optional[str]
    debit_note_result: str
    debit_note_details: Optional[str]
    error_log: Document

    def format(self, invoice_type: str) -> str:
        error_link = frappe.utils.get_link_to_form('Error Log', self.error_log.name)
        return (
            f'<p><strong>{invoice_type}</strong></p>'
            f'<ul>'
            f'<li>Invoice result: {self.invoice_result}</li>'
            f'<li>Credit note result: {self.credit_note_result}</li>'
            f'<li>Debit note result: {self.debit_note_result}</li>'
            f'</ul>'
            f'<p>Please check Error Log {error_link} for ZATCA responses</p>'
        )


def _perform_compliance_checks(
    business_settings_id: str,
    simplified_customer_id: Optional[str],
    standard_customer_id: Optional[str],
    item_id: str,
    tax_category_id: str,
) -> NoReturn:
    # For each invoice type (simplified or standard) we perform three checks: invoice, credit note and debit note
    # For each one of the three checks, we perform three steps (creation, submission, check)
    # So, 9 steps per invoice type. A maximum of 18 steps if we're doing compliance for both. Here we figure out
    # what the progress increment is for each step
    num_steps = 18 if simplified_customer_id and standard_customer_id else 9
    progress_per_step = 100.0 / num_steps
    progress = 0.0

    has_error = False
    try:
        settings = cast(ZATCABusinessSettings, frappe.get_doc('ZATCA Business Settings', business_settings_id))
        simplified_result = None
        standard_result = None

        if simplified_customer_id:
            simplified_result = _perform_compliance_for_invoice_type(
                progress,
                progress_per_step,
                ft('Simplified'),
                simplified_customer_id,
                settings,
                item_id,
                tax_category_id,
            )
            progress += 9 * progress_per_step

        if standard_customer_id:
            standard_result = _perform_compliance_for_invoice_type(
                progress, progress_per_step, ft('Standard'), standard_customer_id, settings, item_id, tax_category_id
            )

        # Submitting the above invoices results in a number of messages about payment reconciliation and the like,
        # and we don't to show those with the result of the compliance check
        frappe.clear_messages()

        message = ''
        if simplified_result:
            message += simplified_result.format(ft('Simplified'))
        if standard_result:
            message += standard_result.format(ft('Standard'))
        frappe.msgprint(message, realtime=True)
    except Exception as e:
        has_error = True
        error_log = frappe.log_error(title='Compliance error')
        error_link = frappe.utils.get_link_to_form('Error Log', error_log.name)
        # Hide progress before showing the error
        _report_progress(ft('Error'), 100)
        frappe.msgprint(
            title=ft('Compliance Error'), msg=f'{str(e)}.\nError log link: {error_link}', indicator='red', realtime=True
        )
    finally:
        # If an error occurs, we hide the progress before showing it, so no need to do it here
        if not has_error:
            _report_progress(ft('Done'), 100)
        clear_additional_fields_ignore_list()
        logger.info('Rolling back')
        frappe.db.rollback()


def _perform_compliance_for_invoice_type(
    progress: float,
    progress_per_step: float,
    invoice_type: str,
    customer_id: str,
    settings: ZATCABusinessSettings,
    item_id: str,
    tax_category_id: str,
) -> _ComplianceResult:
    _report_progress(ft('Creating $type invoice', type=invoice_type), progress)
    invoice = _make_invoice(settings.company, customer_id, item_id, tax_category_id)
    invoice.save()
    progress += progress_per_step

    _report_progress(ft('Submitting $type invoice', type=invoice_type), progress)
    ignore_additional_fields_for_invoice(invoice.name)
    invoice.submit()
    progress += progress_per_step

    _report_progress(ft('Checking $type invoice compliance', type=invoice_type), progress)
    result, details = _check_invoice_compliance(invoice)
    progress += progress_per_step

    # We need to check the credit note and debit note separately, so we roll back to this save point after checking
    # the credit note. Otherwise, the debit note ends up with 0 qty for the item (since the credit note returns it)
    frappe.db.savepoint('before_credit_note')

    _report_progress(ft('Creating $type credit note', type=invoice_type), progress)
    return_invoice = cast(SalesInvoice, make_sales_return(invoice.name))
    return_invoice.custom_return_reason = 'Goods returned'
    return_invoice.set_taxes()
    return_invoice.set_missing_values()
    return_invoice.save()
    progress += progress_per_step

    _report_progress(ft('Submitting $type credit note', type=invoice_type), progress)
    ignore_additional_fields_for_invoice(return_invoice.name)
    return_invoice.submit()
    progress += progress_per_step

    _report_progress(ft('Checking $type credit note compliance', type=invoice_type), progress)
    credit_note_result, credit_note_details = _check_invoice_compliance(return_invoice)
    progress += progress_per_step

    frappe.db.rollback(save_point='before_credit_note')
    _report_progress(ft('Creating $type debit note', type=invoice_type), progress)
    debit_invoice = cast(SalesInvoice, make_sales_return(invoice.name))
    debit_invoice.custom_return_reason = 'Goods returned'
    debit_invoice.is_debit_note = True
    debit_invoice.set_taxes()
    debit_invoice.set_missing_values()
    debit_invoice.save()
    progress += progress_per_step

    _report_progress(ft('Submitting $type debit note', type=invoice_type), progress)
    ignore_additional_fields_for_invoice(debit_invoice.name)
    debit_invoice.submit()
    progress += progress_per_step

    _report_progress(ft('Checking $type debit note compliance', type=invoice_type), progress)
    debit_note_result, debit_note_details = _check_invoice_compliance(debit_invoice)
    progress += progress_per_step

    error_log = frappe.log_error(
        title=ft('$type Compliance Check Result', type=invoice_type),
        message=f'Invoice Result: {result}\n'
        f'{details}\n'
        f'Credit Note Result: {credit_note_result}\n'
        f'{credit_note_details}\n'
        f'Debit Note Result: {debit_note_result}\n'
        f'{debit_note_details}\n',
    )

    return _ComplianceResult(
        result, details, credit_note_result, credit_note_details, debit_note_result, debit_note_details, error_log
    )


def _report_progress(description: str, percent: float) -> None:
    logger.info(f'[Compliance Check] {description} ({percent}%)')
    frappe.publish_progress(title=ft('Compliance Check'), description=description, percent=percent)


def _make_invoice(company: str, customer: str, item: str, tax_category_id: str) -> SalesInvoice:
    invoice = cast(SalesInvoice, frappe.new_doc('Sales Invoice'))
    invoice.company = company
    invoice.customer = customer
    invoice.tax_category = tax_category_id
    invoice.set_taxes()
    invoice.append('items', {'item_code': item, 'qty': 1.0})
    invoice.set_missing_values()
    invoice.save()
    return invoice


def _check_invoice_compliance(invoice: SalesInvoice) -> Tuple[str, Optional[str]]:
    si_additional_fields_doc = cast(SalesInvoiceAdditionalFields, frappe.new_doc('Sales Invoice Additional Fields'))
    si_additional_fields_doc.send_mode = ZatcaSendMode.Compliance
    si_additional_fields_doc.sales_invoice = invoice.name
    si_additional_fields_doc.flags.ignore_permissions = True
    si_additional_fields_doc.insert()
    result = si_additional_fields_doc.submit_to_zatca()
    if is_ok(result):
        zatca_message = frappe.get_value(
            'ZATCA Integration Log',
            {'invoice_additional_fields_reference': si_additional_fields_doc.name},
            ['zatca_message'],
        )
        return result.ok_value, zatca_message

    return result.err_value, None
