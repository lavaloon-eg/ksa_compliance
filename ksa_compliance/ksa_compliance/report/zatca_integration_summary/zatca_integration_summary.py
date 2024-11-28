# Copyright (c) 2024, LavaLoon and contributors
# For license information, please see license.txt
from ksa_compliance.ksa_compliance.report.zatca_integration_details.zatca_integration_details import get_pie_chart_data

import frappe
from datetime import datetime


def execute(filters=None):
    data, chart, report_summary = [], None, []

    if not filters:
        return

    df = datetime.strptime(filters['from_date_filter'], '%Y-%m-%d')
    dt = datetime.strptime(filters['to_date_filter'], '%Y-%m-%d')
    if dt < df:
        frappe.throw(
            msg=f"""Date range must be from {filters['from_date_filter']} to {filters['to_date_filter']}.
                        error_code='InvalidDateRange',
                        code=400
                        """
        )

    data = get_zatca_integration_summary_data(filters=filters)

    if data:
        labels = [row['integration_status'] for row in data]
        values = {row['integration_status']: row['records_count'] for row in data}
        chart = get_pie_chart_data(title='Zatca Integration Status', labels=labels, values=values)
        records_count = sum(row['records_count'] for row in data)

        report_summary = [
            {
                'value': records_count,
                'label': 'Number of records',
                'datatype': 'Number',
            },
        ]

    # return columns, data, message, chart, report_summary, primitive_summary
    return get_columns(), data, None, chart, report_summary


def get_columns():
    return [
        {'fieldname': 'integration_status', 'fieldtype': 'Data', 'label': 'ZATCA Integration status', 'width': 200},
        {'fieldname': 'records_count', 'fieldtype': 'Int', 'label': 'Total Number of invoices', 'width': 150},
        {'fieldname': 'net_total', 'fieldtype': 'Currency', 'label': 'Net Total Amount', 'width': 150},
        {'fieldname': 'total_taxes_and_charges', 'fieldtype': 'Currency', 'label': 'VAT Total Amount', 'width': 150},
        {'fieldname': 'grand_total', 'fieldtype': 'Currency', 'label': 'Grand Total Amount', 'width': 150},
    ]


def get_zatca_integration_summary_data(filters):
    query = """
            SELECT IFNULL(zi.integration_status,'N/A') AS integration_status,
            COUNT(DISTINCT inv.name) AS records_count,
            SUM(inv.net_total) AS net_total,
            SUM(inv.total_taxes_and_charges) AS total_taxes_and_charges,
            SUM(inv.grand_total) AS grand_total
            FROM
            `tabSales Invoice` inv
            LEFT JOIN `tabSales Invoice Additional Fields` zi
            ON inv.name = zi.sales_invoice
            WHERE inv.company = %(company)s
            AND inv.docstatus = 1
            AND inv.posting_date BETWEEN %(from_date)s AND DATE_ADD(%(to_date)s, INTERVAL 1 DAY)
            AND zi.is_latest = 1
            GROUP BY zi.integration_status
          """

    return frappe.db.sql(
        query=query,
        values={
            'from_date': filters['from_date_filter'],
            'to_date': filters['to_date_filter'],
            'company': filters['company_filter'],
        },
        as_dict=1,
    )
