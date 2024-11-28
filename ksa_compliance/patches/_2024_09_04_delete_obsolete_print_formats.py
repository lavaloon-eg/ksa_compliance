import frappe


def execute():
    names = [
        'ZATCA Simplified Sales Invoice',
        'ZATCA Simplified Credit Invoice',
        'ZATCA Simplified Debit Invoice',
        'ZATCA Standard Sales Invoice',
        'ZATCA Standard Credit Invoice',
        'ZATCA Standard Debit Invoice',
    ]
    frappe.db.sql('DELETE FROM `tabPrint Format` WHERE name IN %(names)s', {'names': names})
