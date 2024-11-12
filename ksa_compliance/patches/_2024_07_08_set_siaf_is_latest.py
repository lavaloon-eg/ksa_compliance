import frappe


def execute():
    frappe.db.sql(
        'UPDATE `tabSales Invoice Additional Fields` siaf SET is_latest = 1 '
        'WHERE name = (SELECT name FROM `tabSales Invoice Additional Fields`'
        '              WHERE sales_invoice = siaf.sales_invoice ORDER BY modified DESC LIMIT 1)'
    )
