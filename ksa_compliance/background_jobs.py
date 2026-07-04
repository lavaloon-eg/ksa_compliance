import datetime
from typing import Optional, cast

import frappe
import frappe.utils.background_jobs
from frappe.query_builder import DocType
from frappe.utils import add_to_date, now_datetime
from pypika import Order
from pypika.queries import QueryBuilder
from result import is_ok

from ksa_compliance import logger
from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import (
    SalesInvoiceAdditionalFields,
)
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import (
    ZATCABusinessSettings,
)
from ksa_compliance.ksa_compliance.doctype.zatca_egs.zatca_egs import ZATCAEGS
from ksa_compliance.zatca_live_sync import get_live_zatca_submit_job_id

LIVE_SYNC_BATCH_GRACE_SECONDS = 60


def _is_live_sync_for_siaf(row: dict) -> bool:
    settings = ZATCABusinessSettings.for_invoice(row.get('sales_invoice'), row.get('invoice_doctype'))
    if not settings:
        return False

    is_live_sync = settings.is_live_sync
    if row.get('precomputed_invoice'):
        device_id = frappe.db.get_value('ZATCA Precomputed Invoice', row.precomputed_invoice, 'device_id')
        if device_id:
            egs_settings = ZATCAEGS.for_device(device_id)
            if egs_settings:
                is_live_sync = egs_settings.is_live_sync
    return is_live_sync


def should_skip_live_batch_submission(siaf_name: str) -> str | None:
    """Return skip reason for live sync, or None to proceed with batch submit."""
    row = frappe.db.get_value(
        'Sales Invoice Additional Fields',
        siaf_name,
        ['integration_status', 'creation', 'sales_invoice', 'invoice_doctype', 'precomputed_invoice'],
        as_dict=True,
    )
    if not row or row.integration_status != 'Ready For Batch':
        return None

    if not _is_live_sync_for_siaf(row):
        return None

    job_id = get_live_zatca_submit_job_id(siaf_name)
    if frappe.utils.background_jobs.is_job_enqueued(job_id):
        return f'live RQ job active ({job_id})'

    grace_cutoff = add_to_date(now_datetime(), seconds=-LIVE_SYNC_BATCH_GRACE_SECONDS)
    if row.creation and row.creation > grace_cutoff:
        return f'within {LIVE_SYNC_BATCH_GRACE_SECONDS}s grace period (creation={row.creation})'

    return None


@frappe.whitelist()
def add_batch_to_background_queue(check_date=datetime.date.today()):
    try:
        logger.info('Start Enqueue E-Invoices')
        frappe.enqueue(
            'ksa_compliance.background_jobs.sync_e_invoices',
            check_date=check_date,
            queue='long',
            timeout=3480,  # 58 minutes, so that we can run it hourly
            job_name='Sync E-Invoices',
            deduplicate=True,
            job_id=f'Sending invoices {check_date}',
        )
    except Exception as ex:
        logger.error('An error occurred queueing the job', exc_info=ex)


def sync_e_invoices(
    check_date: Optional[datetime.datetime | datetime.date] = None, batch_size: int = 100, dry_run: bool = False
):
    prefix = '[Dry run] ' if dry_run else ''
    logger.info(f'{prefix}Syncing with ZATCA in batches of {batch_size}')
    if check_date:
        logger.info(f'{prefix}Limiting sync to >= date: {check_date}')

    # We can't use a numerical offset and increment it by the number of records because of the nature of the query.
    # We're querying for draft sales invoice additional fields then submitting them. Let's say we start with offset 0
    # and get 100 sales invoice additional fields. We submit the 100 and increase the offset to 100. Then we query
    # for a 100 **draft** sales invoice additional fields with offset 100, which skips a 100 draft additional sales
    # invoice fields because the 100 that we wanted to skip are now submitted, not draft.
    #
    # If we kept the offset at 0, the loop would never terminate in dry_run mode because we never update status.
    #
    # The solution is to use the creation date itself as an offset/filter. We sort by it ascending, so after every
    # batch we can query for fields whose creation > the last creation in the previous batch
    if isinstance(check_date, datetime.date):
        offset = cast(Optional[datetime.datetime], datetime.datetime.combine(check_date, datetime.time.min))
    else:
        offset = cast(Optional[datetime.datetime], check_date)

    while True:
        query = build_query(offset, batch_size)
        additional_field_docs = query.run(as_dict=True)
        if not additional_field_docs:
            break

        logger.info(f'{prefix}Syncing {len(additional_field_docs)} after date/time {offset}')
        offset = additional_field_docs[-1].creation

        for doc in additional_field_docs:
            try:
                skip_reason = should_skip_live_batch_submission(doc.name)
                if skip_reason:
                    logger.info(f'{prefix}Skipping {doc.name} — {skip_reason}')
                    continue

                logger.info(f'{prefix}Submitting {doc.name}')
                if dry_run:
                    continue

                adf_doc = cast(
                    SalesInvoiceAdditionalFields, frappe.get_doc('Sales Invoice Additional Fields', doc.name)
                )
                result = adf_doc.submit_to_zatca()
                message = result.ok_value if is_ok(result) else result.err_value
                logger.info(f'{prefix}{doc.name}: {message}')
                frappe.db.commit()
            except Exception:
                logger.error(f'{prefix}Error submitting {doc.name}', exc_info=True)
                frappe.db.rollback()

    logger.info(f'{prefix}Sync Done')


def build_query(check_date: Optional[datetime.datetime], limit: int) -> QueryBuilder:
    batch_status = ['Ready For Batch', 'Resend', 'Corrected']
    doctype = DocType('Sales Invoice Additional Fields')
    query = (
        frappe.qb.from_(doctype)
        .select(doctype.name, doctype.creation)
        .where((doctype.integration_status.isin(batch_status)) & (doctype.docstatus == 0))
    )
    if check_date:
        query = query.where(doctype.creation > check_date)
    query = query.orderby(doctype.creation, order=Order.asc).limit(limit)
    return query
