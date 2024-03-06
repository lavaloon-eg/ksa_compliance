import datetime
from typing import Optional

import frappe
from frappe.query_builder import DocType
from pypika import Order
from pypika.queries import QueryBuilder

from ksa_compliance import logger


@frappe.whitelist()
def add_batch_to_background_queue(check_date=datetime.date.today()):
    try:
        logger.info("Start Enqueue E-Invoices")
        frappe.enqueue("ksa_compliance.background_jobs.sync_e_invoices",
                       check_date=check_date,
                       queue="long",
                       timeout=3480,  # 58 minutes, so that we can run it hourly
                       job_name="Sync E-Invoices")
    except Exception as ex:
        logger.error(f"An error occurred queueing the job", exc_info=ex)


def sync_e_invoices(check_date: Optional[datetime.datetime | datetime.date] = None, batch_size: int = 100,
                    dry_run: bool = False):
    prefix = '[Dry run] ' if dry_run else ''
    logger.info(f"{prefix}Syncing with ZATCA in batches of {batch_size}")
    if check_date:
        logger.info(f"{prefix}Limiting sync to >= date: {check_date}")

    offset = 0
    while True:
        query = build_query(check_date, offset, batch_size)
        additional_field_docs = query.run(as_dict=True)
        if not additional_field_docs:
            break

        logger.info(f"{prefix}Syncing {len(additional_field_docs)} at offset {offset}")
        offset += len(additional_field_docs)

        for doc in additional_field_docs:
            try:
                logger.info(f"{prefix}Submitting {doc.name}")
                if dry_run:
                    continue

                adf_doc = frappe.get_doc("Sales Invoice Additional Fields", doc.name)
                adf_doc.submit()
                frappe.db.commit()
            except Exception as e:
                # Review: Should we roll back?
                logger.error(f"{prefix}Error submitting {doc.name}", exc_info=e)

    logger.info(f"{prefix}Sync Done")


def build_query(check_date: datetime.datetime | datetime.date, offset: int, limit: int) -> QueryBuilder:
    batch_status = ["Ready For Batch", "Resend", "Corrected"]
    doctype = DocType("Sales Invoice Additional Fields")
    query = (frappe.qb.from_(doctype).select(doctype.name)
             .where((doctype.integration_status.isin(batch_status)) & (doctype.docstatus == 0)))
    if check_date:
        query = query.where(doctype.creation > check_date)
    query = query.orderby(doctype.creation, order=Order.asc).offset(offset).limit(limit)
    return query
