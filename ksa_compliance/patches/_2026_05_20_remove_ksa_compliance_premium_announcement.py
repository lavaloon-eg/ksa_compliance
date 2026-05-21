import frappe

ANNOUNCEMENT_BLOCK = 'KSA Compliance Premium Announcement'


def execute():
    remove_announcement_block()


def remove_announcement_block():
    if frappe.db.exists('Custom HTML Block', ANNOUNCEMENT_BLOCK):
        frappe.delete_doc('Custom HTML Block', ANNOUNCEMENT_BLOCK, force=True)
