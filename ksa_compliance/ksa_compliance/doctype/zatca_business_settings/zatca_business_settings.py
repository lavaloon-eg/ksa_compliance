# Copyright (c) 2024, Lavaloon and contributors
# For license information, please see license.txt
import logging
from typing import Optional, NoReturn, cast

# import frappe
import frappe
# noinspection PyProtectedMember
from frappe import _
from frappe.model.document import Document
from frappe.utils.logger import get_logger
from result import is_err

import ksa_compliance.zatca_api as api
import ksa_compliance.zatca_cli as cli

logger = get_logger('zatca')
logger.setLevel(logging.INFO)


class ZATCABusinessSettings(Document):
    # Seller Details tab
    company: str
    company_unit: str
    company_unit_serial: str
    company_category: str
    country: str
    country_code: str
    company_address: str
    building_number: Optional[str]
    street: str
    district: Optional[str]
    city: str
    vat_registration_number: str

    # Integration tab
    lava_zatca_path: Optional[str]
    fatoora_server_url: Optional[str]
    csr: Optional[str]
    security_token: Optional[str]
    secret: Optional[str]
    compliance_request_id: Optional[str]
    production_request_id: Optional[str]
    production_security_token: Optional[str]
    production_secret: Optional[str]

    def onboard(self, otp: str) -> NoReturn:
        """Creates a CSR and issues a compliance CSID request. On success, updates the document with the CSR,
        compliance request ID, as well as credentials (security token and secret).

        This is meant for consumption from Desk. It displays an error or a success dialog."""
        if not self.lava_zatca_path:
            frappe.throw(_("Please configure 'Lava Zatca Path'"))

        self._throw_if_api_config_missing()

        csr_result = self._generate_csr()
        compliance_result = api.get_compliance_csid(self.fatoora_server_url, csr_result.csr, otp)
        if is_err(compliance_result):
            frappe.throw(compliance_result.err_value, title=_('Compliance API Error'))

        self.csr = csr_result.csr
        self.security_token = compliance_result.ok_value.security_token
        self.secret = compliance_result.ok_value.secret
        self.compliance_request_id = compliance_result.ok_value.request_id
        self.save()

        frappe.msgprint(_('Onboarding completed successfully'), title=_('Success'))

    def get_production_csid(self, otp: str) -> NoReturn:
        """Uses the compliance response to issue a production CSID. On success, updates the document with the CSID
        request ID and credentials.

        This is meant for consumption from Desk. It displays an error or a success dialog."""
        self._throw_if_api_config_missing()
        if not self.compliance_request_id:
            frappe.throw(_("Please onboard first to generate a 'Compliance Request ID'"))

        csid_result = api.get_production_csid(self.fatoora_server_url, self.compliance_request_id, otp,
                                              self.security_token, self.get_password('secret'))
        if is_err(csid_result):
            frappe.throw(csid_result.err_value, title=_('Production CSID Error'))

        self.production_request_id = csid_result.ok_value.request_id
        self.production_security_token = csid_result.ok_value.security_token
        self.production_secret = csid_result.ok_value.secret
        self.save()

        frappe.msgprint(_("Production CSID generated successfully"), title=_('Success'))

    def _generate_csr(self) -> cli.CsrResult:
        config = frappe.render_template(
            'ksa_compliance/templates/csr-config.properties', is_path=True,
            context={
                'unit_common_name': self.company_unit,  # Review: Same as unit_name
                'unit_serial_number': self.company_unit_serial,
                'vat_number': self.vat_registration_number,
                'unit_name': self.company_unit or 'Main Branch',  # Review: Use default value?
                'organization_name': self.company,
                'country': self.country_code.upper(),
                'invoice_type': '1100',  # Review: Hard-coded
                'address': self._format_address(),
                'category': self.company_category,
            })

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
