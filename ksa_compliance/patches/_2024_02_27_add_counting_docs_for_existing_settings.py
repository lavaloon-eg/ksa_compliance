import frappe


def execute():
    existing_settings = frappe.db.get_all('ZATCA Business Settings', ['name', 'company'])
    if existing_settings:
        for setting in existing_settings:
            max_invoice_counter = 0
            invoice_hash = 'NWZlY2ViNjZmZmM4NmYzOGQ5NTI3ODZjNmQ2OTZjNzljMmRiYzIzOWRkNGU5MWI0NjcyOWQ3M2EyN2ZiNTdlOQ=='

            max_invoice_counter = (
                frappe.db.sql(
                    """
                SELECT MAX(ad.invoice_counter) AS max_invoice_counter
                FROM `tabSales Invoice Additional Fields` AS ad
                LEFT JOIN `tabSales Invoice` AS si
                ON ad.sales_invoice = si.name
                WHERE si.company = %(company)s
            """,
                    {'company': setting.company},
                    as_dict=1,
                )[0].max_invoice_counter
                or 0
            )

            if max_invoice_counter:
                invoice_hash = frappe.db.sql(
                    """
                    SELECT ad.invoice_hash
                    FROM `tabSales Invoice Additional Fields` AS ad
                    LEFT JOIN `tabSales Invoice` AS si
                    ON ad.sales_invoice = si.name
                    WHERE si.company = %(company)s
                    AND ad.invoice_counter = %(max_counter)s            
                """,
                    {'max_counter': max_invoice_counter, 'company': setting.company},
                    as_dict=1,
                )[0].invoice_hash

            if not frappe.db.exists('ZATCA Invoice Counting Settings', setting.name):
                invoice_counting_doc = frappe.new_doc('ZATCA Invoice Counting Settings')
                invoice_counting_doc.business_settings_reference = setting.name
                invoice_counting_doc.invoice_counter = max_invoice_counter
                invoice_counting_doc.previous_invoice_hash = invoice_hash
                invoice_counting_doc.insert(ignore_permissions=True)
