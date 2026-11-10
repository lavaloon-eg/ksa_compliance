# Copyright (c) 2026, LavaLoon and contributors
# For license information, please see license.txt
import base64
import os
import stat
import tempfile
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings
from ksa_compliance.zatca_files import rebase_zatca_tool_path, write_private_file


class TestZatcaFiles(FrappeTestCase):
    def test_write_private_file_is_readable_only_by_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'nested', 'key.privkey')
            write_private_file(path, 'secret')

            with open(path, 'rt') as f:
                self.assertEqual('secret', f.read())
            self.assertEqual(0o600, stat.S_IMODE(os.stat(path).st_mode))
            self.assertEqual(['key.privkey'], os.listdir(os.path.dirname(path)), 'no temp files should be left behind')

    def test_write_private_file_overwrites_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'cert.pem')
            write_private_file(path, b'old')
            write_private_file(path, b'new')
            with open(path, 'rb') as f:
                self.assertEqual(b'new', f.read())

    def test_rebase_moves_automatic_tool_path_to_current_site(self):
        old = '/home/frappe/old-bench/sites/old.site/zatca-tools/zatca-cli-2.10.0/bin/zatca-cli'
        with patch('frappe.get_site_path', side_effect=lambda *parts: os.path.join('./new.site', *parts)):
            rebased = rebase_zatca_tool_path(old)
        self.assertEqual(os.path.abspath('./new.site/zatca-tools/zatca-cli-2.10.0/bin/zatca-cli'), rebased)

    def test_rebase_leaves_manual_paths_alone(self):
        self.assertEqual('/opt/zatca-cli/bin/zatca-cli', rebase_zatca_tool_path('/opt/zatca-cli/bin/zatca-cli'))


class TestZatcaBusinessSettingsFiles(FrappeTestCase):
    @staticmethod
    def _settings(**values) -> ZATCABusinessSettings:
        return frappe.get_doc({'doctype': 'ZATCA Business Settings', **values})

    def test_certificate_pem_wraps_decoded_security_token(self):
        token = base64.b64encode(b'MIIabc').decode()
        self.assertEqual(
            b'-----BEGIN CERTIFICATE-----\nMIIabc\n-----END CERTIFICATE-----',
            ZATCABusinessSettings._certificate_pem(token),
        )
        self.assertIsNone(ZATCABusinessSettings._certificate_pem(None))
        self.assertIsNone(ZATCABusinessSettings._certificate_pem(''))

    def test_ensure_file_restores_missing_file_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'zatca-files', 'a.pem')
            self.assertEqual(path, ZATCABusinessSettings._ensure_file(path, b'restored'))
            with open(path, 'rb') as f:
                self.assertEqual(b'restored', f.read())

            ZATCABusinessSettings._ensure_file(path, b'changed')
            with open(path, 'rb') as f:
                self.assertEqual(b'restored', f.read(), 'an existing file must not be overwritten')

    def test_ensure_file_does_nothing_without_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'missing.pem')
            ZATCABusinessSettings._ensure_file(path, None)
            self.assertFalse(os.path.exists(path))

    def test_rebase_only_applies_to_automatic_setup(self):
        old = '/old/sites/old.site/zatca-tools/cli/bin/zatca-cli'
        self.assertEqual({}, self._settings(cli_setup='Manual', zatca_cli_path=old).rebase_automatic_tool_paths())

        changes = self._settings(
            cli_setup='Automatic', zatca_cli_path=old, java_home='/old/sites/old.site/zatca-tools/jre'
        ).rebase_automatic_tool_paths()
        self.assertEqual({'zatca_cli_path', 'java_home'}, set(changes))
        for path in changes.values():
            self.assertIn(f'{os.sep}zatca-tools{os.sep}', path)
            self.assertNotIn('/old/', path)
