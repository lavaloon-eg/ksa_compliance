from dataclasses import dataclass
from typing import cast, List, Dict, Callable, TypeVar
from urllib.parse import urljoin

import requests
from frappe.utils.logger import get_logger
from requests import HTTPError, Response, JSONDecodeError
from requests.auth import HTTPBasicAuth
from result import Result, Ok, Err

logger = get_logger('zatca')


@dataclass
class ComplianceResult:
    """A successful result from ZATCA for compliance and production CSID"""
    request_id: str
    disposition_message: str
    security_token: str
    secret: str

    @staticmethod
    def from_json(data: dict) -> 'ComplianceResult':
        """Create a [ComplianceResult] from JSON [data]"""
        return ComplianceResult(request_id=data['requestID'], disposition_message=data['dispositionMessage'],
                                security_token=data['binarySecurityToken'], secret=data['secret'])


def get_compliance_csid(server: str, csr: str, otp: str) -> Result[ComplianceResult, str]:
    """Gets a compliance CSID from ZATCA using a CSR and OTP."""
    headers = {
        'Accept-Version': 'V2',
        'OTP': otp,
    }
    body = {'csr': csr}
    return api_call(server, 'compliance', headers, body, ComplianceResult.from_json)


def get_production_csid(server: str, compliance_request_id: str, otp: str, security_token: str,
                        secret: str) -> Result[ComplianceResult, str]:
    """Gets a production CSID from ZATCA for a compliance request."""
    headers = {
        'Accept-Version': 'V2',
        'OTP': otp,
    }
    body = {'compliance_request_id': compliance_request_id}
    auth = HTTPBasicAuth(security_token, secret)
    return api_call(server, 'production/csids', headers, body, ComplianceResult.from_json, auth=auth)


TOk = TypeVar('TOk')


def api_call(server: str, path: str, headers: Dict[str, str], body: Dict[str, str],
             result_builder: Callable[[dict], TOk], auth=None) -> Result[TOk, str]:
    """
    Performs a ZATCA API call and builds a success result using [result_builder]. In case of 400 errors, the
    response is parsed and a combined error is returned.

    Never throws an exception
    """
    if not server.endswith('/'):
        server = server + '/'

    url = urljoin(server, path)

    try:
        response = requests.post(url, headers=headers, json=body, auth=auth)
        response.raise_for_status()
        return Ok(result_builder(response.json()))
    except HTTPError as e:
        logger.error('An HTTP error occurred', exc_info=e)
        if e.response.text:
            logger.info(f'Response: {e.response.text}')

        return Err(try_get_response_error(e.response, str(e)))
    except Exception as e:
        logger.error('An unexpected exception occurred', exc_info=e)
        return Err(str(e))


def try_get_response_error(response: Response, default_error: str) -> str:
    """Tries to extract an error from a ZATCA response. The sandbox API isn't consistent in how it reports errors,
    so this method tries a number of approaches based on the observed error responses."""
    try:
        data = response.json()
        if response.status_code == 400:
            errors = cast(List[str], data.get('errors', []))
            if not errors:
                errors.append(default_error)
            return ', '.join(errors)

        if response.status_code == 500:
            return data.get('message', default_error)

        return default_error
    except JSONDecodeError:
        # If the response is not JSON, we return the content itself as the error
        return response.text
