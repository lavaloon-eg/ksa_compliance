# Copyright (c) 2024, Lavaloon and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime


def execute(filters=None):
    columns, data, chart, report_summary = [], [], None, []
    if not filters:
        return

    df = datetime.strptime(filters['from_date_filter'], '%Y-%m-%d')
    dt = datetime.strptime(filters['to_date_filter'], '%Y-%m-%d')
    if dt < df:
        frappe.throw(
            msg="""To date must be after From date.
                        error_code='InvalidDateRange',
                        code=400
                        """
        )
    try:
        data = get_zatca_integration_details_data(filters=filters)
        columns = get_columns()
        records_count = len(data)
        report_summary = [
            {
                'value': records_count,
                'label': 'Number of records',
                'datatype': 'Number',
            },
        ]

        values = {}
        labels = []
        colors = []
        for row in data:
            if row['integration_status'] not in labels:
                labels.append(row['integration_status'])
            if row['integration_status'] not in values:
                values[row['integration_status']] = 1
            else:
                values[row['integration_status']] += 1

        for label in labels:
            if label == 'Accepted':
                colors.append('green')
            elif label == 'Rejected':
                colors.append('red')
            elif label == 'Resend':
                colors.append('blue')
            elif label == 'Accepted with warnings':
                colors.append('yellow')
        chart = get_pie_chart_data(
            title='Zatca Integration Status', labels=labels, values=values, height=250, colors=colors
        )

        # return columns, data, message, chart, report_summary, primitive_summary
        return columns, data, None, chart, report_summary

    except Exception as ex:
        frappe.throw(msg=f"""{str(ex)}""")


def get_zatca_integration_details_data(filters):
    query = """
                SELECT 
                    inv.name AS invoice_id,
                    IFNULL(zi.integration_status,'N/A') integration_status,
                    inv.posting_date,
                    inv.net_total,
                    inv.total_taxes_and_charges,
                    inv.grand_total
                FROM
                    `tabSales Invoice Additional Fields` zi
                RIGHT JOIN `tabSales Invoice` inv
                ON inv.name = zi.sales_invoice
                WHERE inv.company = %(company)s
                AND inv.posting_date BETWEEN %(from_date)s AND DATE_ADD(%(to_date)s, INTERVAL 1 DAY)
                AND zi.is_latest = 1
                AND (
                (%(integration_status_filter)s = 'All' AND zi.integration_status IN ('All', 'Ready For Batch', 'Resend', 'Accepted with warnings', 'Accepted', 'Rejected', 'Clearance switched off'))
                ) OR
                (
                (%(integration_status_filter)s != 'All' AND zi.integration_status = %(integration_status_filter)s)
                )
            """

    return frappe.db.sql(
        query=query,
        values={
            'from_date': filters['from_date_filter'],
            'to_date': filters['to_date_filter'],
            'company': filters['company_filter'],
            'integration_status_filter': filters['integration_status_filter'],
        },
        as_dict=1,
    )


def get_columns():
    return [
        {
            'label': _('Invoice ID'),
            'fieldname': 'invoice_id',
            'fieldtype': 'Link',
            'options': 'Sales Invoice',
            'width': 200,
        },
        {
            'label': _('ZATCA Integration Status'),
            'fieldname': 'integration_status',
            'fieldtype': 'Data',
            'width': 200,
        },
        {
            'label': _('Posting Date'),
            'fieldname': 'posting_date',
            'fieldtype': 'Date',
            'width': 200,
        },
        {
            'label': _('Net Amount'),
            'fieldname': 'net_total',
            'fieldtype': 'Currency',
            'width': 200,
        },
        {
            'label': _('VAT Amount'),
            'fieldname': 'total_taxes_and_charges',
            'fieldtype': 'Currency',
            'width': 200,
        },
        {
            'label': _('Grand Total'),
            'fieldname': 'grand_total',
            'fieldtype': 'Currency',
            'width': 200,
        },
    ]


def get_pie_chart_data(title, labels: [], values: [], height=250, colors=None):
    options = {
        'title': title,
        'data': {'labels': labels, 'datasets': [{'values': [values[label] for label in labels]}]},
        'type': 'pie',
        'height': height,
        'colors': colors,
    }

    return options
