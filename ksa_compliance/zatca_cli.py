import json
import logging
import os.path
import subprocess
import tempfile
from dataclasses import dataclass
from json import JSONDecodeError
from typing import cast, List, NoReturn

import frappe
# noinspection PyProtectedMember
from frappe import _
from frappe.utils.logger import get_logger

logger = get_logger('zatca')
logger.setLevel(logging.INFO)


@dataclass
class ZatcaResult:
    """Result for an invocation of lava-zatca CLI"""
    is_success: bool
    msg: str
    errors: List[str]

    @property
    def is_failure(self):
        return not self.is_success


@dataclass
class CsrResult:
    """Result for CSR generation invocation to lava-zatca CLI"""
    csr: str
    """The CSR contents, ready to be sent to the compliance API"""

    csr_path: str
    """The path to the CSR file"""

    private_key_path: str
    """The path to the private key file"""


@frappe.whitelist()
def version(zatca_path: str) -> NoReturn:
    """Shows a desk dialog with the version of the Lava ZATCA CLI if found, or an error otherwise"""
    result = run_command(zatca_path, ['-v'])
    frappe.msgprint(result.msg, _("Lava Zatca"))


def generate_csr(lava_zatca_path: str, vat_registration_number: str, config: str) -> CsrResult:
    """
    Generates a CSR for a given VAT registration number. The VAT registration is used to name the resulting
    CSR and private key files.

    Currently, both files are stored in 'sites/' and named '{vat}-.csr' and '{vat}.privkey'

    TODO: Revisit this, especially with respect to the private key. ZATCA requires it to not be exportable.
    """
    config_path = write_temp_file(config, f'csr-{vat_registration_number}.properties')
    csr_path = f'{vat_registration_number}.csr'
    private_key_path = f'{vat_registration_number}.privkey'
    result = run_command(lava_zatca_path, ['csr', '-c', config_path, '-o', csr_path, '-k', private_key_path])
    logger.info(result.msg)
    with open(csr_path, 'rt') as file:
        csr = file.read()
    return CsrResult(csr, csr_path, private_key_path)


def run_command(zatca_path: str, args: List[str]) -> ZatcaResult:
    """Runs a ZATCA command (using lava-zatca CLI) and parses its JSON output. Output is in the form:
    { 'msg': '...',
      'errors': ['...', '...']
    }

    [msg] is a human-friendly message to display to the user.
    [errors] is a (potentially empty) list of errors to display to the user.

    Note that currently there are no error codes or the like, because there's no automatic action that can be performed
    in response to failures. The user has to apply the recommended fixes manually, so we just show the messages and
    errors as is.
    """
    if not os.path.isfile(zatca_path):
        frappe.throw(_("{0} does not exist or is not a file").format(zatca_path))

    full_args = [zatca_path] + args
    logger.info(f'Running: {full_args}')
    proc = subprocess.run(full_args, capture_output=True)
    try:
        result = cast(dict, json.loads(proc.stdout))
    except JSONDecodeError:
        result = {'msg': str(proc.stdout), 'errors': [str(proc.stderr)]}
    except Exception as e:
        result = {'msg': 'An unexpected error occurred', 'errors': [str(e)]}

    if proc.returncode != 0:
        msg = cast(str, result['msg'])
        if result['errors']:
            msg += "<ul>"
        for e in result['errors']:
            msg += f"<li>{e}</li>"
        msg += "</ul>"
        frappe.throw(msg)

    return ZatcaResult(is_success=True, msg=result['msg'], errors=[])


def write_temp_file(content: str, name: str) -> str:
    """Writes the given text [content] into a temporary file named [name]"""
    path = os.path.join(tempfile.gettempdir(), name)
    with open(path, 'wt+') as file:
        file.write(content)
    return path
