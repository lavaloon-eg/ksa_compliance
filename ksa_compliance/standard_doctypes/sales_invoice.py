from datetime import date
from typing import cast

import frappe
import frappe.utils.background_jobs
from erpnext.accounts.doctype.pos_invoice.pos_invoice import POSInvoice
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.selling.doctype.customer.customer import Customer
from frappe import _
from result import is_ok

from ksa_compliance import logger
from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import (
    SalesInvoiceAdditionalFields,
    is_b2b_customer,
)
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings
from ksa_compliance.ksa_compliance.doctype.zatca_egs.zatca_egs import ZATCAEGS
from ksa_compliance.ksa_compliance.doctype.zatca_phase_1_business_settings.zatca_phase_1_business_settings import (
    ZATCAPhase1BusinessSettings,
)
from ksa_compliance.ksa_compliance.doctype.zatca_precomputed_invoice.zatca_precomputed_invoice import (
    ZATCAPrecomputedInvoice,
)

from ksa_compliance.translation import ft

IGNORED_INVOICES = set()


def ignore_additional_fields_for_invoice(name: str) -> None:
    global IGNORED_INVOICES
    IGNORED_INVOICES.add(name)


def clear_additional_fields_ignore_list() -> None:
    global IGNORED_INVOICES
    IGNORED_INVOICES.clear()


def create_sales_invoice_additional_fields_doctype(self: SalesInvoice | POSInvoice, method):
    if self.doctype == 'Sales Invoice' and not _should_enable_zatca_for_invoice(self.name):
        logger.info(f"Skipping additional fields for {self.name} because it's before start date")
        return

    settings = ZATCABusinessSettings.for_invoice(self.name, self.doctype)
    if not settings:
        if ZATCABusinessSettings.is_revoked_for_company(self.company):
            logger.info(f'Skipping additional fields for {self.name} because of revoked ZATCA settings')
            return
        logger.info(f'Skipping additional fields for {self.name} because of missing ZATCA settings')
        return

    if not settings.enable_zatca_integration:
        logger.info(f'Skipping additional fields for {self.name} because ZATCA integration is disabled in settings')
        return

    global IGNORED_INVOICES
    if self.name in IGNORED_INVOICES:
        logger.info(f"Skipping additional fields for {self.name} because it's in the ignore list")
        return

    if self.doctype == 'Sales Invoice' and self.is_consolidated:
        logger.info(f"Skipping additional fields for {self.name} because it's consolidated")
        return

    si_additional_fields_doc = SalesInvoiceAdditionalFields.create_for_invoice(self.name, self.doctype)
    precomputed_invoice = ZATCAPrecomputedInvoice.for_invoice(self.name)
    is_live_sync = settings.is_live_sync
    if precomputed_invoice:
        logger.info(f'Using precomputed invoice {precomputed_invoice.name} for {self.name}')
        si_additional_fields_doc.use_precomputed_invoice(precomputed_invoice)

        egs_settings = ZATCAEGS.for_device(precomputed_invoice.device_id)
        if not egs_settings:
            logger.warning(f'Could not find EGS for device {precomputed_invoice.device_id}')
        else:
            # EGS Setting overrides company-wide setting
            is_live_sync = egs_settings.is_live_sync

    si_additional_fields_doc.insert()
    if is_live_sync:
        # We're running in the context of invoice submission (on_submit hook). We only want to run our ZATCA logic if
        # the invoice submits successfully after on_submit is run successfully from all apps.
        frappe.utils.background_jobs.enqueue(
            _submit_additional_fields, doc=si_additional_fields_doc, enqueue_after_commit=True
        )


def _submit_additional_fields(doc: SalesInvoiceAdditionalFields):
    logger.info(f'Submitting {doc.name}')
    result = doc.submit_to_zatca()
    message = result.ok_value if is_ok(result) else result.err_value
    logger.info(f'Submission result: {message}')


def _should_enable_zatca_for_invoice(invoice_id: str) -> bool:
    start_date = date(2024, 3, 1)

    if frappe.db.table_exists('Vehicle Booking Item Info'):
        # noinspection SqlResolve
        records = frappe.db.sql(
            'SELECT bv.local_trx_date_time FROM `tabVehicle Booking Item Info` bvii '
            'JOIN `tabBooking Vehicle` bv ON bvii.parent = bv.name WHERE bvii.sales_invoice = %(invoice)s',
            {'invoice': invoice_id},
            as_dict=True,
        )
        if records:
            local_date = records[0]['local_trx_date_time'].date()
            return local_date >= start_date

    posting_date = frappe.db.get_value('Sales Invoice', invoice_id, 'posting_date')
    return posting_date >= start_date


def prevent_cancellation_of_sales_invoice(self: SalesInvoice | POSInvoice, method) -> None:
    is_phase_2_enabled_for_company = ZATCABusinessSettings.is_enabled_for_company(self.company)
    if is_phase_2_enabled_for_company:
        frappe.throw(
            msg=_('You cannot cancel sales invoice according to ZATCA Regulations.'),
            title=_('This Action Is Not Allowed'),
        )


def validate_sales_invoice(self: SalesInvoice | POSInvoice, method) -> None:
    valid = True
    is_phase_2_enabled_for_company = ZATCABusinessSettings.is_enabled_for_company(self.company)
    if ZATCAPhase1BusinessSettings.is_enabled_for_company(self.company) or is_phase_2_enabled_for_company:
        if len(self.taxes) == 0:
            frappe.msgprint(
                msg=_('Please include tax rate in Sales Taxes and Charges Table'),
                title=_('Validation Error'),
                indicator='red',
            )
            valid = False

    if is_phase_2_enabled_for_company:
        settings = ZATCABusinessSettings.for_company(self.company)
        if settings.type_of_business_transactions == 'Standard Tax Invoices':
            customer = cast(Customer, frappe.get_doc('Customer', self.customer))
            if not is_b2b_customer(customer):
                frappe.msgprint(
                    ft(
                        'Company <b>$company</b> is configured to use Standard Tax Invoices, which require customers to '
                        'define a VAT number or one of the other IDs. Please update customer <b>$customer</b>',
                        company=self.company,
                        customer=self.customer,
                    )
                )
                valid = False

    if not valid:
        message_log = frappe.get_message_log()
        error_messages = '\n'.join(log['message'] for log in message_log)
        raise frappe.ValidationError(error_messages)
