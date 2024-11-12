import base64
import dataclasses
import traceback
from dataclasses import dataclass
from enum import Enum
from typing import cast, List, Dict, Callable, TypeVar, Optional, Tuple
from urllib.parse import urljoin

import requests
from requests import HTTPError, Response, JSONDecodeError
from requests.auth import HTTPBasicAuth
from result import Result, Ok, Err

from ksa_compliance import logger


class ZatcaSendMode(Enum):
    """Mode used for sending invoice XML to ZATCA. Compliance is for passing compliance checks. Production is regular
    operation"""

    Compliance = 'Compliance'
    Production = 'Production'


@dataclass
class ComplianceResult:
    """A successful result from ZATCA for compliance and production CSID"""

    request_id: str
    disposition_message: str
    security_token: str
    secret: str

    @staticmethod
    def from_json(data: dict, raw_response: str) -> 'ComplianceResult':
        """Create a [ComplianceResult] from JSON [data]"""
        return ComplianceResult(
            request_id=data['requestID'],
            disposition_message=data['dispositionMessage'],
            security_token=data['binarySecurityToken'],
            secret=data['secret'],
        )


@dataclass
class WarningOrError:
    category: str
    code: str
    message: str

    @staticmethod
    def from_json(data: dict | str) -> 'WarningOrError':
        if isinstance(data, str):
            return WarningOrError(category='No Category', code='No Code', message=data)
        return WarningOrError(
            category=data.get('category', 'No Category'),
            code=data.get('code', 'No Code'),
            message=data.get('message', 'No Message'),
        )


@dataclass
class ReportOrClearInvoiceResult:
    status: Optional[str]
    invoice_hash: Optional[str]
    cleared_invoice: Optional[str]
    warnings: List[WarningOrError]
    errors: List[WarningOrError]
    raw_response: str

    def to_json(self) -> dict:
        result = dataclasses.asdict(self)
        del result['raw_response']
        return result

    @staticmethod
    def from_json(data: dict, raw_response: str) -> 'ReportOrClearInvoiceResult':
        # The swagger documentation on  https://sandbox.zatca.gov.sa/IntegrationSandbox says the response should be
        # like this:
        # {
        #   "invoiceHash": "4JFgbmivjFU/otPSMfZCJTSISc123DbdQkOKHLe1J1Q=",
        #   "status": "REPORTED",
        #   "warnings": null,
        #   "errors": []
        # }
        #
        # In practice, we're getting responses like this:
        # {
        #   "validationResults": {
        #       "infoMessages":[],
        #       "warningMessages":[],
        #       "errorMessages":[],
        #       "status":"WARNING"
        #    },
        #   "reportingStatus":"NOT_REPORTED"
        #  }
        #
        # So we're going to try to parse both. Note that for clearance, it's clearanceStatus instead of reportingStatus
        status = data.get('reportingStatus') or data.get('clearanceStatus') or data.get('status')
        invoice_hash = data.get('invoiceHash')
        cleared_invoice = data.get('clearedInvoice')
        warnings, errors = [], []
        if data.get('warnings'):
            warnings = [WarningOrError.from_json(w) for w in data['warnings']]
        if data.get('validationResults') and data.get('validationResults').get('warningMessages'):
            warnings = [WarningOrError.from_json(w) for w in data['validationResults']['warningMessages']]
        if data.get('errors'):
            errors = [WarningOrError.from_json(e) for e in data['errors']]
        if data.get('validationResults') and data.get('validationResults').get('errorMessages'):
            errors = [WarningOrError.from_json(e) for e in data['validationResults']['errorMessages']]
        return ReportOrClearInvoiceResult(
            status, invoice_hash, cleared_invoice, warnings, errors, raw_response=raw_response
        )


@dataclass
class ReportOrClearInvoiceError:
    response: str
    error: str


def get_compliance_csid(server: str, csr: str, otp: str) -> Tuple[Result[ComplianceResult, str], int]:
    """Gets a compliance CSID from ZATCA using a CSR and OTP."""
    headers = {
        'Accept-Version': 'V2',
        'OTP': otp,
    }
    body = {'csr': csr}
    return api_call(server, 'compliance', headers, body, ComplianceResult.from_json, try_get_csid_error)


def get_production_csid(
    server: str, compliance_request_id: str, otp: str, security_token: str, secret: str
) -> Tuple[Result[ComplianceResult, str], int]:
    """Gets a production CSID from ZATCA for a compliance request."""
    headers = {
        'Accept-Version': 'V2',
        'OTP': otp,
    }
    body = {'compliance_request_id': compliance_request_id}
    auth = HTTPBasicAuth(security_token, secret)
    return api_call(
        server, 'production/csids', headers, body, ComplianceResult.from_json, try_get_csid_error, auth=auth
    )


def report_invoice(
    server: str,
    invoice_xml: str,
    invoice_uuid: str,
    invoice_hash: str,
    security_token: str,
    secret: str,
    mode: ZatcaSendMode,
) -> Tuple[Result[ReportOrClearInvoiceResult, ReportOrClearInvoiceError], int]:
    """Reports a simplified invoice to ZATCA"""
    b64_xml = base64.b64encode(invoice_xml.encode()).decode()
    body = {'invoiceHash': invoice_hash, 'uuid': invoice_uuid, 'invoice': b64_xml}
    headers = {
        'Accept-Version': 'V2',
    }

    url = 'invoices/reporting/single' if mode == ZatcaSendMode.Production else 'compliance/invoices'
    return api_call(
        server,
        url,
        headers,
        body,
        ReportOrClearInvoiceResult.from_json,
        try_get_report_or_clear_error,
        auth=HTTPBasicAuth(security_token, secret),
    )


def clear_invoice(
    server: str,
    invoice_xml: str,
    invoice_uuid: str,
    invoice_hash: str,
    security_token: str,
    secret: str,
    mode: ZatcaSendMode,
) -> Tuple[Result[ReportOrClearInvoiceResult, ReportOrClearInvoiceError], int]:
    """Reports a standard invoice to ZATCA"""
    b64_xml = base64.b64encode(invoice_xml.encode()).decode()
    body = {'invoiceHash': invoice_hash, 'uuid': invoice_uuid, 'invoice': b64_xml}
    headers = {
        'Clearance-Status': '1',
        'Accept-Version': 'V2',
    }

    url = 'invoices/clearance/single' if mode == ZatcaSendMode.Production else 'compliance/invoices'
    return api_call(
        server,
        url,
        headers,
        body,
        ReportOrClearInvoiceResult.from_json,
        try_get_report_or_clear_error,
        auth=HTTPBasicAuth(security_token, secret),
    )


TOk = TypeVar('TOk')
TError = TypeVar('TError')


def api_call(
    server: str,
    path: str,
    headers: Dict[str, str],
    body: Dict[str, str],
    result_builder: Callable[[dict, str], TOk],
    error_builder: Callable[[Response | None, Exception | None], TError],
    auth=None,
) -> Tuple[Result[TOk, TError], int]:
    """
    Performs a ZATCA API call and builds a success result using [result_builder]. In case of 400 errors, the
    response is parsed and a combined error is returned.

    Never throws an exception
    """
    if not server.endswith('/'):
        server = server + '/'

    url = urljoin(server, path)

    final_headers = headers.copy()
    final_headers.update({'accept': 'application/json', 'accept-language': 'en'})

    response: Response | None = None
    try:
        response = requests.post(url, headers=final_headers, json=body, auth=auth)
        response.raise_for_status()
        return Ok(result_builder(response.json(), response.text)), response.status_code
    except HTTPError as e:
        error = error_builder(e.response, e)
        logger.error(f'An HTTP error occurred: {error}')
        if e.response.text:
            logger.info(f'Response: {e.response.text}')

        return Err(error), response.status_code
    except Exception as e:
        error = error_builder(response, e)
        logger.error(f'An unexpected error occurred: {error}', exc_info=e)
        status_code = 0
        if response is not None:
            logger.info(f'Response: {response.text}')
            status_code = response.status_code
        return Err(error), status_code


def try_get_csid_error(response: Response | None, exception: Exception | None) -> str:
    """
    Tries to extract an error from a ZATCA response. The sandbox API isn't consistent in how it reports errors,
    so this method tries a number of approaches based on the observed error responses.
    """
    if response is None:
        if exception:
            return ''.join(traceback.format_exception_only(exception))

        return "API call failed but we don't have a response or an exception. This is a bug."

    try:
        data = response.json()
        if response.status_code == 400:
            errors = [WarningOrError.from_json(e) for e in cast(List[dict | str], data.get('errors', []))]
            if errors:
                return ', '.join([e.message for e in errors])

        if response.status_code == 500 and data.get('message'):
            return data['message']

        return response.text
    except JSONDecodeError:
        # If the response is not JSON, we return the content itself as the error
        return response.text


def try_get_report_or_clear_error(response: Response | None, exception: Exception | None) -> ReportOrClearInvoiceError:
    """Tries to extract an error from a ZATCA reporting/clearance response"""
    if response is None:
        if exception:
            return ReportOrClearInvoiceError('', ''.join(traceback.format_exception_only(exception)))

        return ReportOrClearInvoiceError(
            '', "API call failed but we don't have a response or an exception. This is a bug."
        )

    try:
        data = response.json()
        if response.status_code == 400:
            if data.get('validationResults'):
                if data['validationResults'].get('errorMessages'):
                    errors = cast(List[dict], data['validationResults']['errorMessages'])
                    return ReportOrClearInvoiceError(
                        response.text, '\n'.join([e['code'] + ': ' + e['message'] for e in errors])
                    )

        if response.status_code == 500 and data.get('message'):
            return ReportOrClearInvoiceError(response.text, data['message'])
    except JSONDecodeError:
        # If the response is not JSON, we return the content itself as the error
        pass

    return ReportOrClearInvoiceError(response.text, 'An unknown error occurred')
