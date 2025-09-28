import json
import os.path
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from json import JSONDecodeError
from typing import cast, List, NoReturn, Optional

import semantic_version
from result import is_err

import frappe

# noinspection PyProtectedMember
from frappe import _
from ksa_compliance import logger
from ksa_compliance.throw import fthrow
from ksa_compliance.translation import ft
from ksa_compliance.zatca_cli_setup import download_with_progress, extract_archive
from ksa_compliance.zatca_files import get_csr_path, get_private_key_path, get_zatca_tool_path

DEFAULT_CLI_VERSION = '2.10.0'
DEFAULT_JRE_URL = 'https://github.com/adoptium/temurin11-binaries/releases/download/jdk-11.0.23%2B9/OpenJDK11U-jre_x64_linux_hotspot_11.0.23_9.tar.gz'
DEFAULT_CLI_URL = f'https://github.com/lavaloon-eg/zatca-cli/releases/download/{DEFAULT_CLI_VERSION}/zatca-cli-{DEFAULT_CLI_VERSION}.zip'


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
                content += '<ul>'
            for e in self.errors:
                content += f'<li>{e}</li>'
            content += '</ul>'
            fthrow(content, title=ft('ZATCA CLI Error'))


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
class ValidationDetails:
    is_valid: bool
    is_valid_qr: bool
    is_valid_signature: bool
    errors: dict[str, str]
    warnings: dict[str, str]

    @staticmethod
    def from_json(j: dict) -> 'ValidationDetails':
        return ValidationDetails(j['isValid'], j['isValidQr'], j['isValidSignature'], j['errors'], j['warnings'])


@dataclass
class ValidationResult:
    """Result for validating an invoice through lava-zatca CLI"""

    # The following fields are from CLI 2.0.1 and older
    messages: List[str]
    errors_and_warnings: List[str]

    # The following fields are from 2.1.0 and later
    details: Optional[ValidationDetails]

    @staticmethod
    def from_json(j: dict) -> 'ValidationResult':
        details = ValidationDetails.from_json(j['details']) if 'details' in j else None
        return ValidationResult(j['messages'], j['errorsAndWarnings'], details)


@frappe.whitelist()
def check_setup(zatca_cli_path: str, java_home: Optional[str]) -> NoReturn:
    """Shows a desk dialog with the version of the Lava ZATCA CLI if found, or an error otherwise"""
    result = run_command(zatca_cli_path, ['-v'], java_home=java_home)
    result.throw_if_failure()
    frappe.msgprint(result.msg, ft('ZATCA CLI'))


@frappe.whitelist()
def check_validation_details_support(zatca_cli_path: str, java_home: Optional[str]) -> dict:
    result = run_command(zatca_cli_path, ['-v'], java_home=java_home)
    result.throw_if_failure()
    # Version 2.1.0 is the first version to both support validation and include a 'version' in the data payload
    is_supported = result.data and 'version' in result.data
    return {
        'is_supported': is_supported,
        'error': ''
        if is_supported
        else ft('Please update ZATCA CLI to 2.1.0 or later to support blocking on validation'),
    }


def check_pdfa3b_support_or_throw(zatca_cli_path: str, java_home: Optional[str]) -> None:
    """Checks whether PDF/A-3b support is available (version 2.5.0+). Throws a frappe error if it's not supported"""
    result = run_command(zatca_cli_path, ['-v'], java_home=java_home)
    result.throw_if_failure()
    if result.data and 'version' in result.data:
        version = semantic_version.Version(result.data['version'])
        if version >= semantic_version.Version('2.5.0'):
            return

    fthrow(ft('Please update ZATCA CLI to $version or later to support PDF/A-3b generation', version='2.5.0'))


@frappe.whitelist()
def setup(override_cli_download_url: str | None, override_jre_download_url: str | None):
    """Downloads ZATCA CLI and JRE 11 and extracts them into 'sites/zatca'"""

    def progress_callback(description: str, percent: float):
        frappe.publish_progress(title=ft('Setting up CLI'), percent=percent, description=description)

    try:
        directory = get_zatca_tool_path()
        os.makedirs(directory, exist_ok=True)
        jre_url = override_jre_download_url or DEFAULT_JRE_URL
        cli_url = override_cli_download_url or DEFAULT_CLI_URL

        # There are 4 steps mapped to 0-100% progress:
        # 1. JRE download: 0 - 25%
        # 2. JRE extraction: 25 - 50%
        # 3. CLI download: 50 - 75%
        # 4. CLI extraction: 75 - 100%
        jre_result = download_with_progress(
            jre_url, directory, lambda p: progress_callback(ft('Downloading JRE'), p / 4)
        )
        if is_err(jre_result):
            fthrow(jre_result.err_value)

        jre_path = jre_result.ok_value

        progress_callback(ft('Extracting JRE'), 25)
        java_result = extract_archive(jre_path)
        if is_err(java_result):
            fthrow(java_result.err_value)

        java_home = os.path.abspath(java_result.ok_value)
        progress_callback(ft('Extracting JRE'), 50)

        zatca_download_result = download_with_progress(
            cli_url, directory, lambda p: progress_callback(ft('Downloading CLI'), 50 + (p / 4))
        )
        if is_err(zatca_download_result):
            fthrow(zatca_download_result.err_value)

        zatca_path = zatca_download_result.ok_value

        progress_callback(ft('Extracting CLI'), 75)
        zatca_result = extract_archive(zatca_path)
        if is_err(zatca_result):
            fthrow(zatca_result.err_value)

        zatca_bin = os.path.join(os.path.abspath(zatca_result.ok_value), 'bin/zatca-cli')
        if not os.path.isfile(zatca_bin):
            fthrow(ft('Could not find $zatca_bin after extracting ZATCA archive', zatca_bin=zatca_bin))

        # Make ZATCA CLI executable for the current user
        os.chmod(zatca_bin, os.stat(zatca_bin).st_mode | stat.S_IEXEC)

        return {
            'cli_path': zatca_bin,
            'jre_path': os.path.abspath(java_home),
        }
    finally:
        # Whether we finished successfully or due to an error, we report 100% progress to hide the progress bar
        # Thrown errors (frappe.throw) appear behind the progress bar otherwise
        progress_callback(ft('Done'), 100)


def generate_csr(
    zatca_cli_path: str, java_home: Optional[str], file_prefix: str, config: str, simulation=False
) -> CsrResult:
    """
    Generates a CSR. The given prefix is used to name the resulting CSR and private key files.
    """
    config_path = write_temp_file(config, f'{file_prefix}-csr.properties')
    csr_path = get_csr_path(file_prefix)
    private_key_path = get_private_key_path(file_prefix)
    args = ['csr', '-c', config_path, '-o', csr_path, '-k', private_key_path]
    if simulation:
        args.append('-s')
    result = run_command(zatca_cli_path, args, java_home=java_home)
    logger.info(result.msg)
    result.throw_if_failure()
    with open(csr_path, 'rt') as file:
        csr = file.read()
    return CsrResult(csr, csr_path, private_key_path)


def sign_invoice(
    zatca_cli_path: str, java_home: str, invoice_xml: str, cert_path: str, private_key_path: str
) -> SigningResult:
    base_path = os.path.normpath(os.path.join(os.path.dirname(zatca_cli_path), '../'))
    invoice_path = write_temp_file(invoice_xml, 'invoice.xml')
    signed_invoice_path = get_temp_path('signed_invoice.xml')
    result = run_command(
        zatca_cli_path,
        ['sign', '-b', base_path, '-o', signed_invoice_path, '-c', cert_path, '-k', private_key_path, invoice_path],
        java_home=java_home,
    )
    logger.info(result.msg)
    result.throw_if_failure()
    with open(signed_invoice_path, 'rt') as file:
        signed_invoice = file.read()
    return SigningResult(signed_invoice, signed_invoice_path, result.data['hash'], result.data['qrCode'])


def validate_invoice(
    zatca_cli_path: str, java_home: Optional[str], invoice_path: str, cert_path: str, previous_invoice_hash: str
) -> ValidationResult:
    base_path = os.path.normpath(os.path.join(os.path.dirname(zatca_cli_path), '../'))
    result = run_command(
        zatca_cli_path,
        ['validate', '-b', base_path, '-c', cert_path, '-p', previous_invoice_hash, invoice_path],
        java_home=java_home,
    )
    logger.info(result.msg)
    result.throw_if_failure()
    return ValidationResult.from_json(result.data)


def run_command(zatca_cli_path: str, args: List[str], java_home: Optional[str]) -> ZatcaResult:
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
    if not os.path.isfile(zatca_cli_path):
        fthrow(_('{0} does not exist or is not a file').format(zatca_cli_path))

    full_args = [zatca_cli_path] + args
    env = os.environ.copy()
    if java_home:
        env['JAVA_HOME'] = java_home
    logger.info(f'Running: {full_args}')
    proc = subprocess.run(full_args, capture_output=True, env=env)
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


def write_binary_temp_file(content: bytes, name: str) -> str:
    path = get_temp_path(name)
    with open(path, 'wb+') as file:
        file.write(content)
    return path


def get_temp_path(name: str) -> str:
    return tempfile.mktemp(suffix='-' + name)


def convert_to_pdf_a3_b(
    zatca_cli_path: str, java_home: Optional[str], invoice_id: str, pdf_content: bytes, xml_content: str
) -> str:
    pdf = write_binary_temp_file(pdf_content, f'{invoice_id}.pdf')
    invoice_xml = write_temp_file(xml_content, f'{invoice_id}.xml')

    result = run_command(
        zatca_cli_path,
        ['convert-pdf', '-i', invoice_id, '-x', invoice_xml, pdf],
        java_home=java_home,
    )
    logger.info(result.msg)
    result.throw_if_failure()
    return result.data['filePath']
