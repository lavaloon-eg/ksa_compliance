from unittest import TestCase

from ksa_compliance.zatca_cli import default_jre_url


class TestDefaultJreUrl(TestCase):
    def test_arm_servers_get_the_aarch64_jre(self):
        for machine in ('aarch64', 'arm64', 'AARCH64'):
            self.assertIn('OpenJDK11U-jre_aarch64_linux_hotspot', default_jre_url(machine))

    def test_x86_servers_keep_the_x64_jre(self):
        for machine in ('x86_64', 'AMD64'):
            self.assertIn('OpenJDK11U-jre_x64_linux_hotspot', default_jre_url(machine))
