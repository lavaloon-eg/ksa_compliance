import base64
import os
from typing import cast

import frappe
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings


def generate_compliance_cert_if_missing():
    for id in frappe.get_all('ZATCA Business Settings'):
        settings = cast(ZATCABusinessSettings, frappe.get_doc('ZATCA Business Settings', id))
        if bool(settings.security_token) and not os.path.isfile(settings.compliance_cert_path):
            print(f'Generating compliance certificate for {settings.name}')
            with open(settings.compliance_cert_path, 'wb+') as cert:
                cert.write(b'-----BEGIN CERTIFICATE-----\n')
                cert.write(base64.b64decode(settings.security_token))
                cert.write(b'\n-----END CERTIFICATE-----')
