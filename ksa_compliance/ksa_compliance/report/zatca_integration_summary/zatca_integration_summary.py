# Copyright (c) 2024, LavaLoon and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate

CANONICAL_STATUSES = (
    'Ready For Batch',
    'Resend',
    'Accepted with warnings',
    'Accepted',
    'Rejected',
    'Clearance switched off',
    'Not Sended',
    'No Sales Invoice',
)


def execute(filters=None):
    columns = get_columns()
    filters = _normalize_filters(filters)

    if not filters.get('company_filter'):
        return columns, [], None, None, []

    if getdate(filters['to_date_filter']) < getdate(filters['from_date_filter']):
        frappe.throw(_('To Date must be on or after From Date'))

    try:
        data = get_zatca_integration_summary_data(filters=filters)
        chart = None
        report_summary = []

        if data:
            labels = [row['integration_status'] for row in data]
            values = {row['integration_status']: row['records_count'] for row in data}
            chart = get_pie_chart_data(title='Zatca Integration Status', labels=labels, values=values)
            records_count = sum(row['records_count'] for row in data)
            report_summary = [
                {
                    'value': records_count,
                    'label': _('Number of records'),
                    'datatype': 'Number',
                },
            ]

        return columns, data, None, chart, report_summary

    except frappe.ValidationError:
        raise
    except Exception:
        frappe.log_error(
            title='[[zatca_integration_summary.py]] - execute - body',
            message=frappe.get_traceback(),
        )
        frappe.throw(_('Error running Zatca Integration Summary report'))


def _normalize_filters(filters):
    """Apply safe defaults so the report can open before filters are submitted."""
    filters = frappe._dict(filters or {})
    filters.from_date_filter = filters.get('from_date_filter') or frappe.datetime.month_start()
    filters.to_date_filter = filters.get('to_date_filter') or frappe.datetime.now_date()
    filters.company_filter = filters.get('company_filter') or frappe.defaults.get_user_default('Company')
    filters.invoice_doctype = filters.get('invoice_doctype') or 'All'
    return filters


def get_columns():
    return [
        {
            'fieldname': 'integration_status',
            'fieldtype': 'Data',
            'label': _('ZATCA Integration status'),
            'width': 200,
        },
        {
            'fieldname': 'records_count',
            'fieldtype': 'Int',
            'label': _('Total Number of invoices'),
            'width': 150,
        },
        {
            'fieldname': 'net_total',
            'fieldtype': 'Currency',
            'label': _('Net Total Amount'),
            'width': 150,
        },
        {
            'fieldname': 'total_taxes_and_charges',
            'fieldtype': 'Currency',
            'label': _('VAT Total Amount'),
            'width': 150,
        },
        {
            'fieldname': 'grand_total',
            'fieldtype': 'Currency',
            'label': _('Grand Total Amount'),
            'width': 150,
        },
    ]


def get_zatca_integration_summary_data(filters):
    rows = []
    if filters.get('invoice_doctype') in ('All', 'Sales Invoice'):
        rows.extend(get_sales_invoice_rows(filters))
    if filters.get('invoice_doctype') in ('All', 'POS Invoice'):
        rows.extend(get_pos_invoice_rows(filters))
    if filters.get('invoice_doctype') in ('All', 'Payment Entry'):
        rows.extend(get_payment_entry_rows(filters))
    return build_summary_rows(aggregate_by_status(rows))


def _get_common_values(filters):
    return {
        'from_date': filters['from_date_filter'],
        'to_date': filters['to_date_filter'],
        'company': filters['company_filter'],
    }


def _integration_status_case():
    return """
		CASE
			WHEN zi.sales_invoice IS NULL THEN 'Not Sended'
			WHEN IFNULL(zi.integration_status, '') = '' THEN 'No Sales Invoice'
			ELSE zi.integration_status
		END
	"""


def get_sales_invoice_rows(filters):
    query = (
        """
		SELECT
			"""
        + _integration_status_case()
        + """ AS integration_status,
			1 AS records_count,
			inv.net_total,
			inv.total_taxes_and_charges,
			inv.grand_total
		FROM `tabSales Invoice` inv
		LEFT JOIN `tabSales Invoice Additional Fields` zi
			ON zi.sales_invoice = inv.name
			AND zi.invoice_doctype = 'Sales Invoice'
			AND zi.is_latest = 1
		WHERE inv.company = %(company)s
			AND inv.docstatus = 1
			AND inv.posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND NOT EXISTS (
				SELECT 1
				FROM `tabPOS Invoice` pos_map
				WHERE pos_map.consolidated_invoice = inv.name
			)
	"""
    )
    return frappe.db.sql(query, _get_common_values(filters), as_dict=1)


def get_pos_invoice_rows(filters):
    query = (
        """
		SELECT
			"""
        + _integration_status_case()
        + """ AS integration_status,
			1 AS records_count,
			pos.net_total,
			pos.total_taxes_and_charges,
			pos.grand_total
		FROM `tabPOS Invoice` pos
		LEFT JOIN `tabSales Invoice Additional Fields` zi
			ON zi.sales_invoice = pos.name
			AND zi.invoice_doctype = 'POS Invoice'
			AND zi.is_latest = 1
		WHERE pos.company = %(company)s
			AND pos.docstatus = 1
			AND pos.posting_date BETWEEN %(from_date)s AND %(to_date)s
	"""
    )
    return frappe.db.sql(query, _get_common_values(filters), as_dict=1)


def get_payment_entry_rows(filters):
    query = (
        """
		SELECT
			"""
        + _integration_status_case()
        + """ AS integration_status,
			1 AS records_count,
			(pe.paid_amount - IFNULL(pe_tax.total_tax_amount, 0)) AS net_total,
			IFNULL(pe_tax.total_tax_amount, 0) AS total_taxes_and_charges,
			pe.paid_amount AS grand_total
		FROM `tabPayment Entry` pe
		LEFT JOIN (
			SELECT parent, SUM(amount) AS total_tax_amount
			FROM `tabPayment Entry Deduction`
			GROUP BY parent
		) pe_tax ON pe_tax.parent = pe.name
		LEFT JOIN `tabSales Invoice Additional Fields` zi
			ON zi.sales_invoice = pe.name
			AND zi.invoice_doctype = 'Payment Entry'
			AND zi.is_latest = 1
		WHERE pe.company = %(company)s
			AND pe.docstatus = 1
			AND pe.custom_prepayment_invoice = 1
			AND pe.posting_date BETWEEN %(from_date)s AND %(to_date)s
	"""
    )
    return frappe.db.sql(query, _get_common_values(filters), as_dict=1)


def aggregate_by_status(rows):
    aggregated = {}
    for row in rows:
        status = row.get('integration_status') or 'No Sales Invoice'
        if status not in aggregated:
            aggregated[status] = {
                'integration_status': status,
                'records_count': 0,
                'net_total': 0,
                'total_taxes_and_charges': 0,
                'grand_total': 0,
            }
        aggregated[status]['records_count'] += int(row.get('records_count') or 0)
        aggregated[status]['net_total'] += float(row.get('net_total') or 0)
        aggregated[status]['total_taxes_and_charges'] += float(row.get('total_taxes_and_charges') or 0)
        aggregated[status]['grand_total'] += float(row.get('grand_total') or 0)
    return aggregated


def build_summary_rows(aggregated_map):
    rows = []
    for status in CANONICAL_STATUSES:
        rows.append(
            aggregated_map.get(status)
            or {
                'integration_status': status,
                'records_count': 0,
                'net_total': 0,
                'total_taxes_and_charges': 0,
                'grand_total': 0,
            }
        )
    return rows


def get_pie_chart_data(title, labels, values, height=250, colors=None):
    options = {
        'title': title,
        'data': {'labels': labels, 'datasets': [{'values': [values[label] for label in labels]}]},
        'type': 'pie',
        'height': height,
        'colors': colors,
    }
    return options
