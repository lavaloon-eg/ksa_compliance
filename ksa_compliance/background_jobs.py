import frappe
from frappe.query_builder import DocType
import datetime
from ksa_compliance import logger


@frappe.whitelist()
def add_batch_to_background_queue(check_date=datetime.date.today()):
    try:
        logger.info("Start Enqueue E-Invoices")
        frappe.enqueue("ksa_compliance.background_jobs.sync_e_invoices",
                       check_date=check_date,
                       queue="long",
                       timeout=360000,
                       job_name="Sync E-Invoices")
    except Exception as ex:
        import traceback
        logger.error(f"Error Occurred.{traceback.print_exc()}")


def sync_e_invoices(check_date=datetime.date.today()):
    logger.info(f"Starting Job..... {check_date}")
    batch_status = ["Ready For Batch", "Resend", "Corrected"]
    # TODO: Revisit the where clause
    doctype = DocType("Sales Invoice Additional Fields")
    query = (frappe.qb.from_(doctype).select(doctype.name)
    .where(
        (doctype.integration_status.isin(batch_status)) & (doctype.creation > check_date) & (doctype.docstatus == 0)))
    additional_field_docs = query.run(as_dict=True)
    for doc in additional_field_docs:
        adf_doc = frappe.get_doc("Sales Invoice Additional Fields", doc.name)
        adf_doc.submit()
