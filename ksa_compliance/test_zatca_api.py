# Copyright (c) 2026, LavaLoon and contributors
# For license information, please see license.txt
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase
from requests.exceptions import Timeout
from result import is_err

from ksa_compliance.zatca_api import ZATCA_API_TIMEOUT_SECONDS, api_call


class TestZatcaApi(FrappeTestCase):
    def test_post_is_called_with_configured_timeout(self):
        with patch('ksa_compliance.zatca_api.requests.post') as mock_post:
            mock_post.side_effect = Timeout('Connection timed out')
            api_call(
                server='https://example.com/',
                path='invoices/reporting/single',
                headers={},
                body={},
                result_builder=lambda data, raw: data,
                error_builder=lambda response, exception: str(exception),
            )
            self.assertEqual(mock_post.call_args.kwargs.get('timeout'), ZATCA_API_TIMEOUT_SECONDS)

    def test_timeout_produces_err_with_status_code_zero(self):
        with patch('ksa_compliance.zatca_api.requests.post') as mock_post:
            mock_post.side_effect = Timeout('Connection timed out')
            result, status_code = api_call(
                server='https://example.com/',
                path='invoices/reporting/single',
                headers={},
                body={},
                result_builder=lambda data, raw: data,
                error_builder=lambda response, exception: str(exception),
            )
            self.assertTrue(is_err(result))
            self.assertEqual(status_code, 0)
