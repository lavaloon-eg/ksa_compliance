import os
import tempfile
from typing import Union

import frappe


def get_zatca_tool_path(relative_path: str = '.') -> str:
    """
    Returns the path to use for a ZATCA tools (CLI or JRE). We want these files to
    persist across frappe cloud updates but exclude them from backup, so we use the site directory. Previously, we used
    'sites', which was cleaned up after updates so users had to onboard after every update.
    """
    return frappe.get_site_path(os.path.normpath(os.path.join('zatca-tools', relative_path)))


def rebase_zatca_tool_path(path: str) -> str:
    """
    Maps a path to a ZATCA tool (CLI or JRE) saved on another bench/site onto this site's tools directory.

    Automatic CLI setup saves absolute paths in the database, so after a site is transferred they still point at the
    old bench. Paths that aren't under a 'zatca-tools' directory (manual setups) are returned as is.
    """
    _, separator, relative_path = path.partition(f'{os.sep}zatca-tools{os.sep}')
    if not separator:
        return path

    return os.path.abspath(get_zatca_tool_path(relative_path))


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


def write_private_file(path: str, content: Union[str, bytes]) -> None:
    """
    Atomically writes [content] to [path] (creating parent directories), readable only by the current user.

    ZATCA files include private keys, so they're never created world-readable. Writing to a temp file first means a
    crash can't leave a half-written certificate or key behind, which [os.path.isfile] checks would treat as valid.
    """
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    data = content.encode('utf-8') if isinstance(content, str) else content
    fd, temp_path = tempfile.mkstemp(dir=directory)  # mkstemp creates the file with 0600 permissions
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
        os.replace(temp_path, path)
    except BaseException:
        os.unlink(temp_path)
        raise
