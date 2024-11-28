import frappe


def execute():
    print('Updating last attempt with the last modified date.')
    frappe.db.sql("""
        UPDATE `tabSales Invoice Additional Fields` 
        SET last_attempt = modified 
        WHERE last_attempt IS NULL
    """)
