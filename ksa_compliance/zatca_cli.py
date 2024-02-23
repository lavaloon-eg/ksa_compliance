import json
import os.path
import subprocess
import tempfile
from dataclasses import dataclass
from json import JSONDecodeError
from typing import cast, List, NoReturn, Optional

import frappe
# noinspection PyProtectedMember
from frappe import _

from ksa_compliance import logger


@dataclass
class ZatcaResult:
    """Result for an invocation of lava-zatca CLI"""
    is_success: bool
    msg: str
    errors: List[str]
    data: Optional[dict]

    @property
    def is_failure(self):
        return not self.is_success

    def throw_if_failure(self):
        if self.is_failure:
            content = self.msg
            if self.errors:
                content += "<ul>"
            for e in self.errors:
                content += f"<li>{e}</li>"
            content += "</ul>"
            frappe.throw(content)


@dataclass
class CsrResult:
    """Result for CSR generation invocation to lava-zatca CLI"""
    csr: str
    """The CSR contents, ready to be sent to the compliance API"""

    csr_path: str
    """The path to the CSR file"""

    private_key_path: str
    """The path to the private key file"""


@dataclass
class SigningResult:
    """Result for an invoice signing invocation to lava-zatca CLI"""
    signed_invoice_xml: str
    signed_invoice_path: str
    invoice_hash: str
    qr_code: str


@dataclass
class ValidationResult:
    """Result for validating an invoice through lava-zatca CLI"""
    messages: List[str]
    errors_and_warnings: List[str]


@frappe.whitelist()
def version(zatca_path: str) -> NoReturn:
    """Shows a desk dialog with the version of the Lava ZATCA CLI if found, or an error otherwise"""
    result = run_command(zatca_path, ['-v'])
    result.throw_if_failure()
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
    result.throw_if_failure()
    with open(csr_path, 'rt') as file:
        csr = file.read()
    return CsrResult(csr, csr_path, private_key_path)


def sign_invoice(lava_zatca_path: str, invoice_xml: str, cert_path: str, private_key_path: str) -> SigningResult:
    base_path = os.path.normpath(os.path.join(os.path.dirname(lava_zatca_path), '../'))
    invoice_path = write_temp_file(invoice_xml, "invoice.xml")
    signed_invoice_path = get_temp_path('signed_invoice.xml')
    result = run_command(lava_zatca_path,
                         ['sign', '-b', base_path, '-o', signed_invoice_path, '-c', cert_path,
                          '-k', private_key_path, invoice_path])
    logger.info(result.msg)
    result.throw_if_failure()
    with open(signed_invoice_path, 'rt') as file:
        signed_invoice = file.read()
    return SigningResult(signed_invoice, signed_invoice_path, result.data['hash'], result.data['qrCode'])


def validate_invoice(lava_zatca_path: str, invoice_path: str, cert_path: str,
                     previous_invoice_hash: str) -> ValidationResult:
    base_path = os.path.normpath(os.path.join(os.path.dirname(lava_zatca_path), '../'))
    result = run_command(lava_zatca_path, ['validate', '-b', base_path, '-c', cert_path, '-p',
                                           previous_invoice_hash, invoice_path])
    logger.info(result.msg)
    result.throw_if_failure()
    return ValidationResult(result.data['messages'], result.data['errorsAndWarnings'])


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
        return ZatcaResult(is_success=False, msg=result['msg'], errors=result.get('errors', []), data=None)

    return ZatcaResult(is_success=True, msg=result['msg'], errors=[], data=result.get('data'))


def write_temp_file(content: str, name: str) -> str:
    """Writes the given text [content] into a temporary file named [name]"""
    path = get_temp_path(name)
    with open(path, 'wt+') as file:
        file.write(content)
    return path


def get_temp_path(name: str) -> str:
    return tempfile.mktemp(suffix='-' + name)
