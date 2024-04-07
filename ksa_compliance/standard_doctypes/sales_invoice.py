from typing import cast

import frappe
from datetime import date

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
    if not should_enable_zatca_for_invoice(self.name):
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
    si_additional_fields_doc.sales_invoice = self.name

    precomputed_invoice = ZATCAPrecomputedInvoice.for_invoice(self.name)
    is_live_sync = settings.is_live_sync
    if precomputed_invoice:
        logger.info(f"Using precomputed invoice {precomputed_invoice.name} for {self.name}")
        si_additional_fields_doc.precomputed = True
        si_additional_fields_doc.precomputed_invoice = precomputed_invoice.name
        si_additional_fields_doc.invoice_counter = precomputed_invoice.invoice_counter
        si_additional_fields_doc.uuid = precomputed_invoice.invoice_uuid
        si_additional_fields_doc.previous_invoice_hash = precomputed_invoice.previous_invoice_hash
        si_additional_fields_doc.invoice_hash = precomputed_invoice.invoice_hash
        si_additional_fields_doc.invoice_qr = precomputed_invoice.invoice_qr
        si_additional_fields_doc.invoice_xml = precomputed_invoice.invoice_xml

        egs_settings = ZATCAEGS.for_device(precomputed_invoice.device_id)
        if not egs_settings:
            logger.warning(f"Could not find EGS for device {precomputed_invoice.device_id}")
        else:
            # EGS Setting overrides company-wide setting
            is_live_sync = egs_settings.is_live_sync

    if self.customer_address:
        customer_address_doc = frappe.get_doc("Address", self.customer_address)
        address_info = {
            "buyer_additional_number": "not available for now",
            "buyer_street_name": customer_address_doc.get("address_line1"),
            "buyer_additional_street_name": customer_address_doc.get("address_line2"),
            "buyer_building_number": customer_address_doc.get("custom_building_number"),
            "buyer_city": customer_address_doc.get("city"),
            "buyer_postal_code": customer_address_doc.get("pincode"),
            "buyer_district": customer_address_doc.get("custom_area"),
            "buyer_country_code": customer_address_doc.get("country"),
        }
        si_additional_fields_doc.update(address_info)

    # We have to insert before submitting to ensure we can properly update the document with the hash, XML, etc.
    if is_live_sync:
        si_additional_fields_doc.insert(ignore_permissions=True)
        # We need to commit here to ensure saving a draft invoice in live mode before sending it to zatca to handle the Resend scenario.
        frappe.db.commit()
        si_additional_fields_doc.submit()
    else:
        si_additional_fields_doc.integration_status = "Ready For Batch"
        si_additional_fields_doc.insert(ignore_permissions=True)


def should_enable_zatca_for_invoice(invoice_id: str) -> bool:
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
