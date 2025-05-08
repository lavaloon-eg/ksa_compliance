import frappe
from frappe import _

def execute():
    """Add initial data for ZATCA Feedback Settings"""
    if not frappe.db.exists("ZATCA Feedback Settings"):
        doc = frappe.new_doc("ZATCA Feedback Settings")
        doc.update({
            "recipient_emails": "ksa_compliance@lavaloon.com",
            "lavaloon_contact_page": "https://lavaloon.com/contact-us",
            "max_file_size_mb": 5,
            "max_number_of_files": 3
        })
        doc.insert()
        frappe.db.commit() 