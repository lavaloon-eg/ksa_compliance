import frappe


def execute():
    no_of_docs = len(frappe.get_all('Sales Invoice Additional Fields', {'integration_status': ''}, pluck='name'))
    print(f'Update {no_of_docs} Sales Invoice Additional Fields integration status field.')
    frappe.db.sql("""
        UPDATE 
            `tabSales Invoice Additional Fields` SET integration_status = 'Resend', docstatus = 0 
        WHERE 
            integration_status = ''
    """)
