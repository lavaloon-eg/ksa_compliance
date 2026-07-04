# Copyright (c) 2024, Lavaloon and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters=None):
    columns = get_columns()
    filters = _normalize_filters(filters)

    if not filters.get('company_filter'):
        return columns, [], None, None, []

    if getdate(filters['to_date_filter']) < getdate(filters['from_date_filter']):
        frappe.throw(_('To Date must be on or after From Date'))

    try:
        data = get_zatca_integration_details_data(filters=filters)
        data = apply_status_filter(data, filters.get('integration_status_filter'))
        records_count = len(data)
        report_summary = [
            {
                'value': records_count,
                'label': _('Number of records'),
                'datatype': 'Number',
            },
        ]

        values = {}
        labels = []
        colors = []
        for row in data:
            status = row.get('integration_status')
            if status not in labels:
                labels.append(status)
            values[status] = values.get(status, 0) + 1

        for label in labels:
            if label == 'Accepted':
                colors.append('green')
            elif label == 'Rejected':
                colors.append('red')
            elif label == 'Resend':
                colors.append('blue')
            elif label == 'Accepted with warnings':
                colors.append('yellow')

        chart = (
            get_pie_chart_data(
                title='Zatca Integration Status',
                labels=labels,
                values=values,
                height=250,
                colors=colors,
            )
            if labels
            else None
        )

        return columns, data, None, chart, report_summary

    except frappe.ValidationError:
        raise
    except Exception:
        frappe.log_error(
            title='[[zatca_integration_details.py]] - execute - body',
            message=frappe.get_traceback(),
        )
        frappe.throw(_('Error running Zatca Integration Details report'))


def _normalize_filters(filters):
    """Apply safe defaults so the report can open before filters are submitted."""
    filters = frappe._dict(filters or {})
    filters.from_date_filter = filters.get('from_date_filter') or frappe.datetime.month_start()
    filters.to_date_filter = filters.get('to_date_filter') or frappe.datetime.now_date()
    filters.company_filter = filters.get('company_filter') or frappe.defaults.get_user_default('Company')
    filters.integration_status_filter = filters.get('integration_status_filter') or 'All'
    filters.invoice_doctype = filters.get('invoice_doctype') or 'All'
    filters.validated_filter = filters.get('validated_filter') or 'All'
    return filters


def get_zatca_integration_details_data(filters):
    data = []
    if filters.get('invoice_doctype') in ('All', 'Sales Invoice'):
        data.extend(get_sales_invoice_rows(filters))
    if filters.get('invoice_doctype') in ('All', 'POS Invoice'):
        data.extend(get_pos_invoice_rows(filters))
    if filters.get('invoice_doctype') in ('All', 'Payment Entry'):
        data.extend(get_payment_entry_rows(filters))
    data = apply_validated_filter(data, filters.get('validated_filter'))
    return data


def apply_status_filter(rows, status_filter):
    if not status_filter or status_filter == 'All':
        return rows
    return [row for row in rows if row.get('integration_status') == status_filter]


def apply_validated_filter(rows, validated_filter):
    if not validated_filter or validated_filter == 'All':
        return rows
    return [row for row in rows if row.get('validated') == validated_filter]


def _get_common_values(filters):
    values = {
        'from_date': filters['from_date_filter'],
        'to_date': filters['to_date_filter'],
        'company': filters['company_filter'],
    }
    if filters.get('branch_filter'):
        values['branch'] = filters['branch_filter']
    return values


def _get_branch_condition(filters, table_alias):
    if not filters.get('branch_filter'):
        return ''
    if table_alias == 'inv':
        return 'AND inv.branch = %(branch)s'
    if table_alias == 'pos':
        return 'AND pos.branch = %(branch)s'
    return ''


def _integration_status_case():
    return """
		CASE
			WHEN zi.sales_invoice IS NULL THEN 'Not Sended'
			WHEN IFNULL(zi.integration_status, '') = '' THEN 'No Sales Invoice'
			ELSE zi.integration_status
		END
	"""


def _validated_case():
    return """
		CASE
			WHEN zi.last_attempt IS NULL THEN 'Not Validated'
			WHEN DATE(base_doc.posting_date) = DATE(zi.last_attempt) THEN 'Validated'
			ELSE 'Not Validated'
		END
	"""


def get_sales_invoice_rows(filters):
    branch_condition = _get_branch_condition(filters, 'inv')
    query = (
        """
		SELECT
			'Sales Invoice' AS invoice_doctype,
			inv.name AS invoice_id,
			"""
        + _integration_status_case()
        + """
			 AS integration_status,
			"""
        + _validated_case()
        + """
			 AS validated,
			inv.posting_date,
			zi.last_attempt AS custom_zatca_siaf_date,
			inv.branch,
			inv.customer,
			'Customer' AS party_doctype,
			inv.net_total,
			inv.total_taxes_and_charges,
			inv.grand_total,
			zi.name AS custom_zatca_siaf
		FROM `tabSales Invoice` inv
		LEFT JOIN `tabSales Invoice Additional Fields` zi
			ON zi.sales_invoice = inv.name
			AND zi.invoice_doctype = 'Sales Invoice'
			AND zi.is_latest = 1
		LEFT JOIN `tabSales Invoice` base_doc
			ON base_doc.name = inv.name
		WHERE inv.company = %(company)s
			AND inv.docstatus = 1
			AND inv.posting_date BETWEEN %(from_date)s AND %(to_date)s
			"""
        + branch_condition
        + """
			AND NOT EXISTS (
				SELECT 1
				FROM `tabPOS Invoice` pos_map
				WHERE pos_map.consolidated_invoice = inv.name
			)
	"""
    )
    return frappe.db.sql(query, _get_common_values(filters), as_dict=1)


def get_pos_invoice_rows(filters):
    branch_condition = _get_branch_condition(filters, 'pos')
    query = (
        """
		SELECT
			'POS Invoice' AS invoice_doctype,
			pos.name AS invoice_id,
			"""
        + _integration_status_case()
        + """
			 AS integration_status,
			"""
        + _validated_case()
        + """
			 AS validated,
			pos.posting_date,
			zi.last_attempt AS custom_zatca_siaf_date,
			pos.branch,
			pos.customer,
			'Customer' AS party_doctype,
			pos.net_total,
			pos.total_taxes_and_charges,
			pos.grand_total,
			zi.name AS custom_zatca_siaf
		FROM `tabPOS Invoice` pos
		LEFT JOIN `tabSales Invoice Additional Fields` zi
			ON zi.sales_invoice = pos.name
			AND zi.invoice_doctype = 'POS Invoice'
			AND zi.is_latest = 1
		LEFT JOIN `tabPOS Invoice` base_doc
			ON base_doc.name = pos.name
		WHERE pos.company = %(company)s
			AND pos.docstatus = 1
			AND pos.posting_date BETWEEN %(from_date)s AND %(to_date)s
			"""
        + branch_condition
        + """
	"""
    )
    return frappe.db.sql(query, _get_common_values(filters), as_dict=1)


def get_payment_entry_rows(filters):
    query = (
        """
		SELECT
			'Payment Entry' AS invoice_doctype,
			pe.name AS invoice_id,
			"""
        + _integration_status_case()
        + """
			 AS integration_status,
			"""
        + _validated_case()
        + """
			 AS validated,
			pe.posting_date,
			zi.last_attempt AS custom_zatca_siaf_date,
			NULL AS branch,
			pe.party AS customer,
			pe.party_type AS party_doctype,
			(pe.paid_amount - IFNULL(pe_tax.total_tax_amount, 0)) AS net_total,
			IFNULL(pe_tax.total_tax_amount, 0) AS total_taxes_and_charges,
			pe.paid_amount AS grand_total,
			zi.name AS custom_zatca_siaf
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
		LEFT JOIN `tabPayment Entry` base_doc
			ON base_doc.name = pe.name
		WHERE pe.company = %(company)s
			AND pe.docstatus = 1
			AND pe.custom_prepayment_invoice = 1
			AND pe.posting_date BETWEEN %(from_date)s AND %(to_date)s
	"""
    )
    return frappe.db.sql(query, _get_common_values(filters), as_dict=1)


def get_columns():
    return [
        {
            'label': _('Document Type'),
            'fieldname': 'invoice_doctype',
            'fieldtype': 'Data',
            'width': 140,
        },
        {
            'label': _('Document'),
            'fieldname': 'invoice_id',
            'fieldtype': 'Dynamic Link',
            'options': 'invoice_doctype',
            'width': 200,
        },
        {
            'label': _('ZATCA Integration Status'),
            'fieldname': 'integration_status',
            'fieldtype': 'Data',
            'width': 170,
        },
        {
            'label': _('Date Validation'),
            'fieldname': 'validated',
            'fieldtype': 'Data',
            'width': 140,
        },
        {
            'label': _('Posting Date'),
            'fieldname': 'posting_date',
            'fieldtype': 'Date',
            'width': 130,
        },
        {
            'label': _('ZATCA Date'),
            'fieldname': 'custom_zatca_siaf_date',
            'fieldtype': 'Datetime',
            'width': 185,
        },
        {
            'label': _('Branch'),
            'fieldname': 'branch',
            'fieldtype': 'Link',
            'options': 'Branch',
            'width': 120,
        },
        {
            'label': _('Customer'),
            'fieldname': 'customer',
            'fieldtype': 'Dynamic Link',
            'options': 'party_doctype',
            'width': 180,
        },
        {
            'label': _('Net Amount'),
            'fieldname': 'net_total',
            'fieldtype': 'Currency',
            'width': 130,
        },
        {
            'label': _('VAT Amount'),
            'fieldname': 'total_taxes_and_charges',
            'fieldtype': 'Currency',
            'width': 130,
        },
        {
            'label': _('Grand Total'),
            'fieldname': 'grand_total',
            'fieldtype': 'Currency',
            'width': 130,
        },
        {
            'label': _('ZATCA SIAF'),
            'fieldname': 'custom_zatca_siaf',
            'fieldtype': 'Link',
            'options': 'Sales Invoice Additional Fields',
            'width': 220,
        },
    ]


def get_pie_chart_data(title, labels, values, height=250, colors=None):
    options = {
        'title': title,
        'data': {'labels': labels, 'datasets': [{'values': [values[label] for label in labels]}]},
        'type': 'pie',
        'height': height,
        'colors': colors,
    }

    return options
