import frappe


def execute():
    frappe.db.sql(
        'CREATE UNIQUE INDEX IF NOT EXISTS lava_zatca_precomputed_invoice_uuid ON '
        '`tabZATCA Precomputed Invoice` (invoice_uuid)'
    )

    frappe.db.sql(
        'CREATE UNIQUE INDEX IF NOT EXISTS lava_sales_invoice_additional_fields_uuid ON '
        '`tabSales Invoice Additional Fields` (uuid)'
    )
