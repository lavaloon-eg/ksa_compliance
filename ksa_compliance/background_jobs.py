import datetime
from typing import Optional, cast

import frappe
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
from frappe.query_builder import DocType
from frappe.utils import get_url_to_list, now_datetime
from frappe.utils.user import get_users_with_role
from pypika import Order
from pypika.queries import QueryBuilder
from result import is_ok

from ksa_compliance import logger
from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import (
    SalesInvoiceAdditionalFields,
)

# Statuses that are eligible to be picked up by the hourly sync batch
BATCH_ELIGIBLE_STATUSES = ['Ready For Batch', 'Resend', 'Corrected']

# How long a batch-eligible Sales Invoice Additional Fields can sit unsynced before we alert
STUCK_INVOICE_THRESHOLD_HOURS = 6


@frappe.whitelist()
def add_batch_to_background_queue(check_date=None):
    if check_date is None:
        check_date = datetime.date.today()
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
    doctype = DocType('Sales Invoice Additional Fields')
    query = (
        frappe.qb.from_(doctype)
        .select(doctype.name, doctype.creation)
        .where((doctype.integration_status.isin(BATCH_ELIGIBLE_STATUSES)) & (doctype.docstatus == 0))
    )
    if check_date:
        query = query.where(doctype.creation > check_date)
    query = query.orderby(doctype.creation, order=Order.asc).limit(limit)
    return query


def find_stuck_invoices(threshold_hours: int = STUCK_INVOICE_THRESHOLD_HOURS) -> list[dict]:
    """
    Finds draft Sales Invoice Additional Fields in a batch-eligible status whose creation date is
    older than threshold_hours, ordered oldest first.
    """
    cutoff = now_datetime() - datetime.timedelta(hours=threshold_hours)
    doctype = DocType('Sales Invoice Additional Fields')
    query = (
        frappe.qb.from_(doctype)
        .select(doctype.name, doctype.creation, doctype.integration_status)
        .where(
            (doctype.integration_status.isin(BATCH_ELIGIBLE_STATUSES))
            & (doctype.docstatus == 0)
            & (doctype.creation < cutoff)
        )
        .orderby(doctype.creation, order=Order.asc)
    )
    return query.run(as_dict=True)


def notify_stuck_invoices(threshold_hours: int = STUCK_INVOICE_THRESHOLD_HOURS) -> None:
    """
    Alerts System Managers when Sales Invoice Additional Fields have been waiting to sync with ZATCA
    for longer than threshold_hours. Writes one Error Log entry and one desk notification per run;
    it doesn't track what it already reported, so a stall still stuck on the next run raises again.
    """
    stuck = find_stuck_invoices(threshold_hours)
    if not stuck:
        return

    oldest = stuck[0]
    oldest_age_hours = (now_datetime() - oldest.creation).total_seconds() / 3600
    list_url = get_url_to_list('Sales Invoice Additional Fields')
    message = (
        f'{len(stuck)} Sales Invoice Additional Fields have been waiting to sync with ZATCA for more '
        f'than {threshold_hours} hour(s). The oldest ({oldest.name}) has been waiting '
        f'{oldest_age_hours:.1f} hours. This usually means the sync scheduler has stopped, or invoices '
        f'are stuck cycling in Resend. List: {list_url}'
    )
    frappe.log_error(title='ZATCA Sync Stuck', message=message)

    recipients = get_users_with_role('System Manager')
    if recipients:
        enqueue_create_notification(
            recipients,
            {
                'type': 'Alert',
                'subject': f'{len(stuck)} invoice(s) stuck syncing with ZATCA',
                'document_type': 'Sales Invoice Additional Fields',
                'document_name': oldest.name,
                'email_content': message,
            },
        )
