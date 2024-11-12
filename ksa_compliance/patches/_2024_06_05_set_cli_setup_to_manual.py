import frappe


def execute():
    frappe.db.sql("UPDATE `tabZATCA Business Settings` SET cli_setup = 'Manual'")
