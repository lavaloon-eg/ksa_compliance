import frappe
from frappe.query_builder import DocType
from frappe.utils import getdate
from frappe.utils.logger import get_logger
from ksa_compliance.endpoints import request_reporting_api
from ksa_compliance.generate_xml import generate_xml_file


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
    except Exception as ex:
        import traceback
        logger.error(f"Error Occurred.{traceback.print_exc()}")


@frappe.whitelist()
def sync_e_invoices(check_date):
    check_date = getdate(check_date, parse_day_first=True)
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


def get_integration_log_status(code):
    status_map = {
        200: "Approved",
        202: "Approved with warning",
        401: "Rejected",
        400: "Rejected",
        500: "Failed"
    }
    if code in status_map:
        return status_map[code]
    else:
        return None
