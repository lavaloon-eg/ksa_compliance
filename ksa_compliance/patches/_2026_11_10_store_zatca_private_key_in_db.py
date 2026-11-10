import os

import frappe
from frappe.utils.password import set_encrypted_password
from pathvalidate import sanitize_filename

from ksa_compliance.zatca_files import get_private_key_path


def execute():
    """
    Stores the private key of already onboarded settings in the database (encrypted), so their ZATCA files can be
    restored if the site is moved to another bench. Must run while the key file still exists on disk.
    """
    for name in frappe.get_all('ZATCA Business Settings', filters={'private_key': ['is', 'not set']}, pluck='name'):
        key_path = get_private_key_path(sanitize_filename(name))
        if not os.path.isfile(key_path):
            continue

        with open(key_path, 'rt') as key_file:
            set_encrypted_password('ZATCA Business Settings', name, key_file.read(), 'private_key')
