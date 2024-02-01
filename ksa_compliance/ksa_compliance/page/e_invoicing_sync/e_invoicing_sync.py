import frappe
from frappe.query_builder import DocType
from frappe.utils.logger import get_logger
from ksa_compliance.endpoints import request_reporting_api
from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import (
    construct_einvoice_data)
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
        adf_doc = frappe.get_doc("Sales Invoice Additional Fields", doc.name)
        einvoice = construct_einvoice_data(adf_doc)
        frappe.log_error("ZATCA Result LOG", message=einvoice.result)
        frappe.log_error("ZATCA Error LOG", message=einvoice.error_dic)
        invoice_xml = generate_xml_file(einvoice.result)
        response = request_reporting_api(invoice_xml, uuid=adf_doc.get("uuid"))
        log_status = get_integration_log_status(response.status_code)
        response = response.json()
        integration_dict = {"doctype": "ZATCA Integration Log",
                            "invoice_reference": adf_doc.get("sales_invoice"),
                            "invoice_additional_fields_reference": adf_doc.get("name"),
                            "zatca_message": str(response),
                            "zatca_status": response.get("reportingStatus"),
                            "status": log_status if log_status else "Pending"
                            }
        integration_doc = frappe.get_doc(integration_dict)
        integration_doc.insert()


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
