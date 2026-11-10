import frappe

from ksa_compliance.patches._2025_05_11_add_feedback_links_block import execute as add_feedback_links_block
from ksa_compliance.patches._2026_03_16_add_zatca_images import execute as add_images


def after_install():
    print('Starting post-installation setup...')
    print('Adding custom HTML block for feedback and link section...')
    add_feedback_links_block()
    print("Adding Add images from the app's public folder to File Documents...")
    add_images()
    print('Post-installation setup complete.')


def after_migrate():
    """
    Makes ZATCA work on a site that was moved to another bench: the files and tools under the site directory aren't
    part of backups, so recreate what we can from the database and fix the saved tool paths.
    """
    from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import (
        ZATCABusinessSettings,
    )

    for name in frappe.get_all('ZATCA Business Settings', pluck='name'):
        try:
            settings: ZATCABusinessSettings = frappe.get_doc('ZATCA Business Settings', name)
            settings.restore_missing_files()
            if changes := settings.rebase_automatic_tool_paths():
                settings.db_set(changes, update_modified=False)
        except Exception:
            # A problem with one company's settings must never fail the whole migration
            frappe.log_error(title=f'Failed to restore ZATCA files for {name}')
