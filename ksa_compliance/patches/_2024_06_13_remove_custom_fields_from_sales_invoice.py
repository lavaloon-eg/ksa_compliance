import frappe


def execute():
    fields = [
        'Sales Invoice-custom_qr_code',
        'Sales Invoice Item-custom_tax_total',
        'Sales Invoice Item-custom_total_after_tax',
        'Sales Invoice Item-custom_column_break_sm8qq',
        'Sales Invoice Item-custom_section_break_ejvy9',
    ]
    for field in fields:
        print(f'Deleting custom field {field} if it exists')
        if frappe.db.exists('Custom Field', field):
            frappe.delete_doc('Custom Field', field)

    # Commit before schema changes
    frappe.db.commit()

    print('Removing QR code custom field from sales invoice')
    frappe.db.sql("""
                    ALTER TABLE `tabSales Invoice`
                    DROP COLUMN IF EXISTS `custom_qr_code`
                """)

    print('Removing custom_tax_total and custom_total_after_tax from sales invoice items')
    frappe.db.sql("""
                    ALTER TABLE `tabSales Invoice Item`
                    DROP COLUMN IF EXISTS `custom_tax_total`,
                    DROP COLUMN IF EXISTS `custom_total_after_tax`
                """)
