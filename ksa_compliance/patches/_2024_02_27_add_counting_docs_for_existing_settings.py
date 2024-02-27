import frappe


def execute():
    first_previous_hash = "NWZlY2ViNjZmZmM4NmYzOGQ5NTI3ODZjNmQ2OTZjNzljMmRiYzIzOWRkNGU5MWI0NjcyOWQ3M2EyN2ZiNTdlOQ=="
    existing_settings = frappe.db.get_all("ZATCA Business Settings", ["name", "company"])
    if existing_settings:
        for setting in existing_settings:
            sales_invoice_ids = frappe.db.get_list("Sales Invoice", {"company": setting.company}, pluck="name")

            additional_doc_data = frappe.db.sql("""
                SELECT MAX(invoice_counter) AS max_invoice_counter, invoice_hash 
                FROM `tabSales Invoice Additional Fields`
                WHERE sales_invoice IN %(sales_invoice_ids)s
            """, {"sales_invoice_ids": sales_invoice_ids}, as_dict=1)

            if not frappe.db.exists("ZATCA Invoice Counting Settings", setting.name):
                invoice_counting_doc = frappe.new_doc("ZATCA Invoice Counting Settings")
                invoice_counting_doc.business_settings_reference = setting.name
                invoice_counting_doc.invoice_counter = (
                    additional_doc_data[0].max_invoice_counter if additional_doc_data[0].max_invoice_counter else 0)
                invoice_counting_doc.previous_invoice_hash = (
                    additional_doc_data[0].invoice_hash if additional_doc_data[
                        0].invoice_hash else first_previous_hash)
                invoice_counting_doc.insert(ignore_permissions=True)
