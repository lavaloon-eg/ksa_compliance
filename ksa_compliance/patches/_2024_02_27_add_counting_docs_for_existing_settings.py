import frappe


def execute():
    existing_settings = frappe.db.get_all("ZATCA Business Settings")
    if existing_settings:
        for setting in existing_settings:
            if not frappe.db.exists("ZATCA Invoice Counting Settings", setting.name):
                invoice_counting_doc = frappe.new_doc("ZATCA Invoice Counting Settings")
                invoice_counting_doc.business_settings_reference = setting.name
                invoice_counting_doc.previous_invoice_hash = "NWZlY2ViNjZmZmM4NmYzOGQ5NTI3ODZjNmQ2OTZjNzljMmRiYzIzOWRkNGU5MWI0NjcyOWQ3M2EyN2ZiNTdlOQ=="
                invoice_counting_doc.insert(ignore_permissions=True)
