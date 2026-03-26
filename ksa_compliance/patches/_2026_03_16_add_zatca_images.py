import os

import frappe


def execute():
    """Add zatca images from the app's public folder to File Documents."""
    images = ['zatca-icon.png']
    app_path = frappe.get_app_path('ksa_compliance')
    base_path = os.path.join(app_path, 'public', 'images')

    if not os.path.exists(base_path):
        frappe.log_error(message=f'Images folder not found: {base_path}', title='ksa_compliance patch')
        return

    for filename in images:
        if frappe.db.exists('File', {'file_name': filename}):
            frappe.log(f'Image "{filename}" already exists. Skipping upload.')
            continue

        full_path = os.path.join(base_path, filename)
        if os.path.isfile(full_path):
            # nosemgrep: frappe-semgrep-rules.rules.security.frappe-security-file-traversal
            with open(full_path, 'rb') as file:
                file_data = file.read()
                file_doc = frappe.get_doc(
                    {'doctype': 'File', 'file_name': filename, 'is_private': 0, 'content': file_data}
                )
                file_doc.insert(ignore_permissions=True)
                frappe.log(f'Added image {filename} to File Documents.')
