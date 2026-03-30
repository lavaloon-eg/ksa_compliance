import os

import frappe


def execute():
    """Add zatca images from the app's public folder to File Documents. Also remove any old versions of the image if they exist."""
    images_to_add = ['zatca-icon.svg']
    images_to_delete = ['zatca-icon.png']
    app_path = frappe.get_app_path('ksa_compliance')
    base_path = os.path.join(app_path, 'public', 'images')

    if not os.path.exists(base_path):
        frappe.log_error(message=f'Images folder not found: {base_path}', title='ksa_compliance patch')
        return

    for filename in images_to_add:
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

    for filename in images_to_delete:
        if frappe.db.exists('File', {'file_name': filename}):
            files_to_delete = frappe.get_all('File', filters={'file_name': filename})
            for file in files_to_delete:
                file_doc = frappe.get_doc('File', file.get('name'))
                file_doc.delete(ignore_permissions=True)
                frappe.log(f'Deleted old image {filename} from File Documents. File ID: {file_doc.name}')
        else:
            frappe.log(f'Image "{filename}" not found. No deletion needed.')
