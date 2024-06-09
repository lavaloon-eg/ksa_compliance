from datetime import date
from typing import cast

import frappe
import frappe.utils.background_jobs
from frappe import _
from result import is_ok

from ksa_compliance import logger
from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import \
    SalesInvoiceAdditionalFields
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings
from ksa_compliance.ksa_compliance.doctype.zatca_egs.zatca_egs import ZATCAEGS
from ksa_compliance.ksa_compliance.doctype.zatca_precomputed_invoice.zatca_precomputed_invoice import \
    ZATCAPrecomputedInvoice

IGNORED_INVOICES = set()


def ignore_additional_fields_for_invoice(name: str) -> None:
    global IGNORED_INVOICES
    IGNORED_INVOICES.add(name)


def clear_additional_fields_ignore_list() -> None:
    global IGNORED_INVOICES
    IGNORED_INVOICES.clear()


def create_sales_invoice_additional_fields_doctype(self, method):
    if not _should_enable_zatca_for_invoice(self.name):
        logger.info(f"Skipping additional fields for {self.name} because it's before start date")
        return

    settings = ZATCABusinessSettings.for_invoice(self.name)
    if not settings:
        logger.info(f"Skipping additional fields for {self.name} because of missing ZATCA settings")
        return

    global IGNORED_INVOICES
    if self.name in IGNORED_INVOICES:
        logger.info(f"Skipping additional fields for {self.name} because it's in the ignore list")
        return

    si_additional_fields_doc = cast(SalesInvoiceAdditionalFields, frappe.new_doc("Sales Invoice Additional Fields"))
    # We do not expect people to create SIAF manually, so nobody has permission to create one
    si_additional_fields_doc.flags.ignore_permissions = True
    si_additional_fields_doc.sales_invoice = self.name

    precomputed_invoice = ZATCAPrecomputedInvoice.for_invoice(self.name)
    is_live_sync = settings.is_live_sync
    if precomputed_invoice:
        logger.info(f"Using precomputed invoice {precomputed_invoice.name} for {self.name}")
        si_additional_fields_doc.use_precomputed_invoice(precomputed_invoice)

        egs_settings = ZATCAEGS.for_device(precomputed_invoice.device_id)
        if not egs_settings:
            logger.warning(f"Could not find EGS for device {precomputed_invoice.device_id}")
        else:
            # EGS Setting overrides company-wide setting
            is_live_sync = egs_settings.is_live_sync

    si_additional_fields_doc.integration_status = "Ready For Batch"
    si_additional_fields_doc.insert()
    if is_live_sync:
        # We're running in the context of invoice submission (on_submit hook). We only want to run our ZATCA logic if
        # the invoice submits successfully after on_submit is run successfully from all apps.
        frappe.utils.background_jobs.enqueue(_submit_additional_fields, doc=si_additional_fields_doc,
                                             enqueue_after_commit=True)


def _submit_additional_fields(doc: SalesInvoiceAdditionalFields):
    logger.info(f'Submitting {doc.name}')
    result = doc.submit_to_zatca()
    message = result.ok_value if is_ok(result) else result.err_value
    logger.info(f'Submission result: {message}')


def _should_enable_zatca_for_invoice(invoice_id: str) -> bool:
    start_date = date(2024, 3, 1)

    if frappe.db.table_exists('Vehicle Booking Item Info'):
        records = frappe.db.sql(
            "SELECT bv.local_trx_date_time FROM `tabVehicle Booking Item Info` bvii "
            "JOIN `tabBooking Vehicle` bv on bvii.parent = bv.name WHERE bvii.sales_invoice = %(invoice)s",
            {'invoice': invoice_id}, as_dict=True)
        if records:
            local_date = records[0]['local_trx_date_time'].date()
            return local_date >= start_date

    posting_date = frappe.db.get_value('Sales Invoice', invoice_id, 'posting_date')
    return posting_date >= start_date


def calculate_tax_amount(self, method):
    if self.items:
        for item in self.items:
            if item.item_tax_template:
                item_tax_rate = get_tax_template_rate(item.item_tax_template)
            else:
                item_tax_rate = sum(account.rate for account in self.taxes)
            if self.taxes[0].included_in_print_rate:
                item.custom_tax_total = item.amount - item.net_amount
            else:
                item.custom_tax_total = (item.net_amount * item_tax_rate) / 100
            item.custom_total_after_tax = item.custom_tax_total + item.net_amount


def get_tax_template_rate(template_id: str) -> float:
    item_tax_template = frappe.get_doc("Item Tax Template", template_id)
    if len(item_tax_template.taxes) > 1:
        frappe.throw(
            msg="""
                One or more items have a tax template with multiple tax accounts which is not currently 
                supported. Please contact the vendor.
                """,
            title="Multiple tax accounts found"
        )
    if item_tax_template.disabled:
        frappe.throw("One or more items has disabled tax template", title="Disabled tax template")
    return item_tax_template.taxes[0].tax_rate


def prevent_cancellation_of_sales_invoice(self, method) -> None:
    frappe.throw(msg=_("You cannot cancel sales invoice according to ZATCA Regulations."),
                 title=_("This Action Is Not Allowed"))

def validate_tax_category(self, method):
    if not self.tax_category:
        frappe.throw(msg=_("Please choose a Tax Category"),
                     title=_("Tax Category Missing"))