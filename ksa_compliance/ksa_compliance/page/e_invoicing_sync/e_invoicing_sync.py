from typing import cast

import frappe
from frappe.query_builder import DocType
from frappe.utils.logger import get_logger

from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import \
    SalesInvoiceAdditionalFields
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings


def logging():
    return get_logger("sync-e-invoices")


@frappe.whitelist()
def add_batch_to_background_queue(check_date):
    logger = logging()
    try:
        logger.info("Start Enqueue E-Invoices")
        frappe.enqueue("ksa_compliance.ksa_compliance.page.e_invoicing_sync.e_invoicing_sync.sync_e_invoices",
                       check_date=check_date,
                       queue="long",
                       timeout=360000,
                       job_name="Sync E-Invoices")
    except Exception:
        import traceback
        logger.error(f"Error Occurred.{traceback.print_exc()}")


@frappe.whitelist()
def sync_e_invoices(check_date):
    # TODO: Check the sync mode in settings
    doctype = DocType("ZATCA Integration Log")
    query = (
        frappe.qb.from_(doctype)
        .select(doctype.invoice_additional_fields_reference.as_("ref_id"))
    )
    synced_invoices_refs = [doc.ref_id for doc in query.run(as_dict=True)]
    doctype = DocType("Sales Invoice Additional Fields")
    query = (frappe.qb.from_(doctype)
             .select(doctype.name)
             .where(doctype.name.notin(synced_invoices_refs)))
    additional_field_docs = query.run(as_dict=True)
    for doc in additional_field_docs:
        adf_doc = cast(SalesInvoiceAdditionalFields, frappe.get_doc("Sales Invoice Additional Fields", doc.name))
        settings = ZATCABusinessSettings.for_invoice(adf_doc.sales_invoice)
        if not settings:
            continue

        adf_doc.send_to_zatca(settings)
        frappe.db.commit()
