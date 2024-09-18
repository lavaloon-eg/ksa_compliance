import os

import frappe


def get_zatca_tool_path(relative_path: str = '.') -> str:
    """
    Returns the path to use for a ZATCA tools (CLI or JRE). We want these files to
    persist across frappe cloud updates but exclude them from backup, so we use the site directory. Previously, we used
    'sites', which was cleaned up after updates so users had to onboard after every update.
    """
    return frappe.get_site_path(os.path.normpath(os.path.join('zatca-tools', relative_path)))


def get_zatca_file_path(relative_path: str = '.') -> str:
    """
    Returns the path to use for a ZATCA file (certificate, key, etc.). We want these files to
    persist across frappe cloud updates but exclude them from backup, so we use the site directory. Previously, we used
    'sites', which was cleaned up after updates so users had to onboard after every update.
    """
    return frappe.get_site_path(os.path.normpath(os.path.join('zatca-files', relative_path)))


def get_sandbox_private_key_path():
    return get_zatca_file_path('sandbox_private_key.pem')


def get_csr_path(file_prefix: str) -> str:
    return get_zatca_file_path(f'{file_prefix}.csr')


def get_cert_path(file_prefix: str) -> str:
    return get_zatca_file_path(f'{file_prefix}.pem')


def get_compliance_cert_path(file_prefix: str) -> str:
    return get_zatca_file_path(f'{file_prefix}-compliance.pem')


def get_private_key_path(file_prefix) -> str:
    return get_zatca_file_path(f'{file_prefix}.privkey')
