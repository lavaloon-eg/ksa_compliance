import os
import subprocess
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from ksa_compliance.zatca_cli import (
    ZATCA_CLI_TIMEOUT_SECONDS,
    ZatcaResult,
    convert_to_pdf_a3_b,
    get_temp_path,
    reserve_temp_path,
    run_command,
    sign_invoice,
    write_binary_temp_file,
    write_temp_file,
)


class TestRunCommandTimeout(FrappeTestCase):
    @patch('ksa_compliance.zatca_cli.os.path.isfile', return_value=True)
    @patch('ksa_compliance.zatca_cli.subprocess.run', side_effect=subprocess.TimeoutExpired(cmd='zatca-cli', timeout=1))
    def test_timeout_produces_failure_result_not_an_exception(self, mock_run, mock_isfile):
        result = run_command('/fake/zatca-cli', ['-v'], java_home=None)

        self.assertIsInstance(result, ZatcaResult)
        self.assertTrue(result.is_failure)
        self.assertIsNone(result.data)

    @patch('ksa_compliance.zatca_cli.os.path.isfile', return_value=True)
    @patch('ksa_compliance.zatca_cli.subprocess.run')
    def test_subprocess_run_receives_configured_timeout(self, mock_run, mock_isfile):
        mock_run.return_value.stdout = b'{"msg": "ok", "data": {}}'
        mock_run.return_value.returncode = 0

        run_command('/fake/zatca-cli', ['-v'], java_home=None)

        self.assertEqual(mock_run.call_args.kwargs['timeout'], ZATCA_CLI_TIMEOUT_SECONDS)


class TestTempPathCreation(FrappeTestCase):
    def test_get_temp_path_creates_the_file_atomically(self):
        path = get_temp_path('foo.xml')
        try:
            self.assertTrue(os.path.exists(path))
        finally:
            os.remove(path)

    def test_reserve_temp_path_does_not_leave_a_file_behind(self):
        path = reserve_temp_path('signed_invoice.xml')
        self.assertFalse(os.path.exists(path))
        self.assertTrue(path.endswith('-signed_invoice.xml'))


class TestSignInvoiceCleanup(FrappeTestCase):
    @patch('ksa_compliance.zatca_cli.run_command')
    def test_removes_invoice_temp_file_even_when_signing_fails(self, mock_run_command):
        mock_run_command.return_value = ZatcaResult(is_success=False, msg='Signing failed', errors=[], data=None)

        captured_paths = []
        real_write_temp_file = write_temp_file

        def spy_write_temp_file(content, name):
            path = real_write_temp_file(content, name)
            captured_paths.append(path)
            return path

        with patch('ksa_compliance.zatca_cli.write_temp_file', side_effect=spy_write_temp_file):
            with self.assertRaises(Exception):
                sign_invoice('/fake/zatca-cli', None, '<xml/>', '/fake/cert.pem', '/fake/key.privkey')

        self.assertEqual(len(captured_paths), 1)
        self.assertFalse(os.path.exists(captured_paths[0]))


class TestConvertToPdfA3bCleanup(FrappeTestCase):
    @patch('ksa_compliance.zatca_cli.run_command')
    def test_removes_input_temp_files_after_a_successful_conversion(self, mock_run_command):
        mock_run_command.return_value = ZatcaResult(
            is_success=True, msg='Converted', errors=[], data={'filePath': '/fake/output.pdf'}
        )

        captured_paths = []
        real_write_binary_temp_file = write_binary_temp_file
        real_write_temp_file = write_temp_file

        def spy_write_binary_temp_file(content, name):
            path = real_write_binary_temp_file(content, name)
            captured_paths.append(path)
            return path

        def spy_write_temp_file(content, name):
            path = real_write_temp_file(content, name)
            captured_paths.append(path)
            return path

        with patch('ksa_compliance.zatca_cli.write_binary_temp_file', side_effect=spy_write_binary_temp_file):
            with patch('ksa_compliance.zatca_cli.write_temp_file', side_effect=spy_write_temp_file):
                result_path = convert_to_pdf_a3_b('/fake/zatca-cli', None, 'SINV-001', b'%PDF-1.4', '<xml/>')

        self.assertEqual(result_path, '/fake/output.pdf')
        self.assertEqual(len(captured_paths), 2)
        for path in captured_paths:
            self.assertFalse(os.path.exists(path))
