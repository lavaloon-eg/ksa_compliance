# Copyright (c) 2024, LavaLoon and contributors
# For license information, please see license.txt
import base64
import os
from typing import Optional, NoReturn, cast

# import frappe
import frappe
# noinspection PyProtectedMember
from frappe import _
from frappe.model.document import Document
from result import is_err

import ksa_compliance.zatca_api as api
import ksa_compliance.zatca_cli as cli
from ksa_compliance import logger
from ksa_compliance.invoice import InvoiceMode


class ZATCABusinessSettings(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from ksa_compliance.ksa_compliance.doctype.additional_seller_ids.additional_seller_ids import AdditionalSellerIDs

        additional_street: DF.Data | None
        building_number: DF.Data | None
        city: DF.Data | None
        company: DF.Link
        company_address: DF.Link
        company_category: DF.Data
        company_unit: DF.Data
        company_unit_serial: DF.Data
        compliance_request_id: DF.Data | None
        country: DF.Link
        country_code: DF.Data | None
        csr: DF.SmallText | None
        currency: DF.Link
        district: DF.Data | None
        enable_zatca_integration: DF.Check
        fatoora_server_url: DF.Data | None
        lava_zatca_path: DF.Data | None
        other_ids: DF.Table[AdditionalSellerIDs]
        postal_code: DF.Data | None
        production_request_id: DF.Data | None
        production_secret: DF.Password | None
        production_security_token: DF.SmallText | None
        secret: DF.Password | None
        security_token: DF.SmallText | None
        seller_name: DF.Data
        street: DF.Data | None
        sync_with_zatca: DF.Literal["Live", "Batches"]
        type_of_business_transactions: DF.Literal["Let the system decide (both)", "Simplified Tax Invoices", "Standard Tax Invoices"]
        validate_generated_xml: DF.Check
        vat_registration_number: DF.Data
    # end: auto-generated types

    def after_insert(self):
        invoice_counting_doc = frappe.new_doc("ZATCA Invoice Counting Settings")
        invoice_counting_doc.business_settings_reference = self.name
        invoice_counting_doc.invoice_counter = 0
        invoice_counting_doc.previous_invoice_hash = \
            "NWZlY2ViNjZmZmM4NmYzOGQ5NTI3ODZjNmQ2OTZjNzljMmRiYzIzOWRkNGU5MWI0NjcyOWQ3M2EyN2ZiNTdlOQ=="
        invoice_counting_doc.insert(ignore_permissions=True)

    @property
    def is_live_sync(self) -> bool:
        return self.sync_with_zatca.lower() == 'live'

    @property
    def invoice_mode(self) -> InvoiceMode:
        return InvoiceMode.from_literal(self.type_of_business_transactions)

    @property
    def has_production_csid(self) -> bool:
        return (bool(self.production_security_token) and bool(self.production_secret) and
                bool(self.production_request_id))

    @property
    def cert_path(self) -> str:
        return f'{self.vat_registration_number}.pem'

    @property
    def compliance_cert_path(self) -> str:
        return f'{self.vat_registration_number}-compliance.pem'

    @property
    def private_key_path(self) -> str:
        if self.is_sandbox_server:
            return self._sandbox_private_key_path

        return f'{self.vat_registration_number}.privkey'

    @property
    def is_sandbox_server(self) -> bool:
        return self.fatoora_server_url.startswith('https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal')

    @property
    def _sandbox_private_key_path(self) -> str:
        """
        Returns the path of the sandbox private key

        The sandbox environment returns a fixed certificate that corresponds to this private key. If we try to sign
        with the real private key, signature validation will fail
        """
        key = ("MHQCAQEEIL14JV+5nr/sE8Sppaf2IySovrhVBtt8+yz"
               "+g4NRKyz8oAcGBSuBBAAKoUQDQgAEoWCKa0Sa9FIErTOv0uAkC1VIKXxU9nPpx2vlf4yhMejy8c02XJblDq7tPydo8mq0ahOMmNo8gwni7Xt1KT9UeA==")
        path = 'sandbox_private_key.pem'
        if not os.path.isfile(path):
            with open(path, 'wb') as f:
                f.write(key.encode('utf-8'))
        return path

    def onboard(self, otp: str) -> NoReturn:
        """Creates a CSR and issues a compliance CSID request. On success, updates the document with the CSR,
        compliance request ID, as well as credentials (security token and secret).

        This is meant for consumption from Desk. It displays an error or a success dialog."""
        if not self.lava_zatca_path:
            frappe.throw(_("Please configure 'Lava Zatca Path'"))

        self._throw_if_api_config_missing()

        csr_result = self._generate_csr()
        compliance_result, status_code = api.get_compliance_csid(self.fatoora_server_url, csr_result.csr, otp)
        if is_err(compliance_result):
            frappe.throw(compliance_result.err_value, title=_('Compliance API Error'))

        self.csr = csr_result.csr
        self.security_token = compliance_result.ok_value.security_token
        self.secret = compliance_result.ok_value.secret
        self.compliance_request_id = compliance_result.ok_value.request_id
        self.save()

        with open(self.compliance_cert_path, 'wb+') as cert:
            cert.write(b'-----BEGIN CERTIFICATE-----\n')
            cert.write(base64.b64decode(compliance_result.ok_value.security_token))
            cert.write(b'\n-----END CERTIFICATE-----')

        frappe.msgprint(_('Onboarding completed successfully'), title=_('Success'))

    def get_production_csid(self, otp: str) -> NoReturn:
        """Uses the compliance response to issue a production CSID. On success, updates the document with the CSID
        request ID and credentials.

        This is meant for consumption from Desk. It displays an error or a success dialog."""
        self._throw_if_api_config_missing()
        if not self.compliance_request_id:
            frappe.throw(_("Please onboard first to generate a 'Compliance Request ID'"))

        csid_result, status_code = api.get_production_csid(self.fatoora_server_url, self.compliance_request_id, otp,
                                                           self.security_token, self.get_password('secret'))
        if is_err(csid_result):
            frappe.throw(csid_result.err_value, title=_('Production CSID Error'))

        self.production_request_id = csid_result.ok_value.request_id
        self.production_security_token = csid_result.ok_value.security_token
        self.production_secret = csid_result.ok_value.secret
        self.save()

        with open(self.cert_path, 'wb+') as cert:
            cert.write(b'-----BEGIN CERTIFICATE-----\n')
            cert.write(base64.b64decode(csid_result.ok_value.security_token))
            cert.write(b'\n-----END CERTIFICATE-----')

        frappe.msgprint(_("Production CSID generated successfully"), title=_('Success'))

    @property
    def csr_config(self) -> dict:
        return {
            'unit_common_name': self.company_unit,  # Review: Same as unit_name
            'unit_serial_number': self.company_unit_serial,
            'vat_number': self.vat_registration_number,
            'unit_name': self.company_unit or 'Main Branch',  # Review: Use default value?
            'organization_name': self.company,
            'country': self.country_code.upper(),
            'invoice_type': '0100',  # Review: Hard-coded
            'address': self._format_address(),
            'category': self.company_category,
        }

    @staticmethod
    def for_invoice(invoice_id: str) -> Optional['ZATCABusinessSettings']:
        company_id = frappe.db.get_value("Sales Invoice", invoice_id, ["company"])
        if not company_id:
            return None

        return ZATCABusinessSettings.for_company(company_id)

    @staticmethod
    def for_company(company_id: str) -> Optional['ZATCABusinessSettings']:
        business_settings_id = frappe.db.get_value('ZATCA Business Settings', filters={'company': company_id})
        if not business_settings_id:
            return None

        return cast(ZATCABusinessSettings, frappe.get_doc("ZATCA Business Settings", business_settings_id))

    def _generate_csr(self) -> cli.CsrResult:
        config = frappe.render_template('ksa_compliance/templates/csr-config.properties', is_path=True,
                                        context=self.csr_config)

        logger.info(f"CSR config: {config}")
        return cli.generate_csr(self.lava_zatca_path, self.vat_registration_number, config)

    def _format_address(self) -> str:
        """
        Formats an address for use in ZATCA in the form 'Building number, street, district, city'

        TODO: We should use a national short address instead (https://splonline.com.sa/en/national-address-1/) if
          available. It should be added to the Address doctype.
        """
        address = ''
        if self.building_number:
            address += self.building_number + ' '

        address += self.street
        if self.district:
            address += ', ' + self.district

        address += ', ' + self.city
        return address

    def _throw_if_api_config_missing(self) -> None:
        if not self.fatoora_server_url:
            frappe.throw(_("Please configure 'Fatoora Server URL'"))


@frappe.whitelist()
def fetch_company_addresses(company_name):
    company_list_dict = frappe.get_all("Dynamic Link", filters={"link_name": company_name}, fields=["parent"])
    company_list = [address.parent for address in company_list_dict]
    return company_list


@frappe.whitelist()
def onboard(business_settings_id: str, otp: str) -> NoReturn:
    settings = cast(ZATCABusinessSettings, frappe.get_doc('ZATCA Business Settings', business_settings_id))
    settings.onboard(otp)


@frappe.whitelist()
def get_production_csid(business_settings_id: str, otp: str) -> NoReturn:
    settings = cast(ZATCABusinessSettings, frappe.get_doc('ZATCA Business Settings', business_settings_id))
    settings.get_production_csid(otp)
