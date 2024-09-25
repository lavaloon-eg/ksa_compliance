# Copyright (c) 2024, Lavaloon and contributors
# For license information, please see license.txt
from __future__ import annotations

import base64
import html
import uuid
from io import BytesIO
from typing import cast, Optional, Literal

import frappe
import frappe.utils.background_jobs
import pyqrcode
from erpnext.accounts.doctype.pos_invoice.pos_invoice import POSInvoice
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.selling.doctype.customer.customer import Customer
from frappe import _
from frappe.contacts.doctype.address.address import Address
from frappe.core.doctype.file.file import File
from frappe.model.document import Document
from frappe.utils import now_datetime, get_link_to_form, strip
from result import is_err, Result, Err, Ok, is_ok

from ksa_compliance import logger
from ksa_compliance import zatca_api as api
from ksa_compliance import zatca_cli as cli
from ksa_compliance.generate_xml import generate_xml_file
from ksa_compliance.invoice import InvoiceMode, InvoiceType
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import (
    ZATCABusinessSettings)
from ksa_compliance.ksa_compliance.doctype.zatca_egs.zatca_egs import ZATCAEGS
from ksa_compliance.ksa_compliance.doctype.zatca_integration_log.zatca_integration_log import ZATCAIntegrationLog
from ksa_compliance.ksa_compliance.doctype.zatca_precomputed_invoice.zatca_precomputed_invoice import \
    ZATCAPrecomputedInvoice
from ksa_compliance.output_models.e_invoice_output_model import Einvoice
from ksa_compliance.translation import ft
from ksa_compliance.zatca_api import ReportOrClearInvoiceError, ReportOrClearInvoiceResult, ZatcaSendMode

# These are the possible statuses resulting from a submission to ZATCA. Note that this is a subset of
# [SalesInvoiceAdditionalFields.integration_status]
ZatcaIntegrationStatus = Literal["Resend", "Accepted with warnings", "Accepted", "Rejected", "Clearance switched off"]


class SalesInvoiceAdditionalFields(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from ksa_compliance.ksa_compliance.doctype.additional_seller_ids.additional_seller_ids import AdditionalSellerIDs

        allowance_indicator: DF.Check
        allowance_vat_category_code: DF.Data | None
        amended_from: DF.Link | None
        buyer_additional_number: DF.Data | None
        buyer_additional_street_name: DF.Data | None
        buyer_building_number: DF.Data | None
        buyer_city: DF.Data | None
        buyer_country_code: DF.Data | None
        buyer_district: DF.Data | None
        buyer_postal_code: DF.Data | None
        buyer_province_state: DF.Data | None
        buyer_street_name: DF.Data | None
        buyer_vat_registration_number: DF.Data | None
        charge_indicator: DF.Check
        charge_vat_category_code: DF.Data | None
        code_for_allowance_reason: DF.Data | None
        fatoora_invoice_discount_amount: DF.Float
        integration_status: DF.Literal["", "Ready For Batch", "Resend", "Corrected", "Accepted with warnings", "Accepted", "Rejected", "Clearance switched off"]
        invoice_counter: DF.Int
        invoice_doctype: DF.Literal["Sales Invoice", "POS Invoice"]
        invoice_hash: DF.Data | None
        invoice_line_allowance_reason: DF.Data | None
        invoice_line_allowance_reason_code: DF.Data | None
        invoice_line_charge_amount: DF.Float
        invoice_line_charge_base_amount: DF.Float
        invoice_line_charge_base_amount_reason: DF.Data | None
        invoice_line_charge_base_amount_reason_code: DF.Data | None
        invoice_line_charge_indicator: DF.Data | None
        invoice_line_charge_percentage: DF.Percent
        invoice_type_code: DF.Data | None
        invoice_type_transaction: DF.Data | None
        invoice_xml: DF.LongText | None
        is_latest: DF.Check
        last_attempt: DF.Datetime | None
        other_buyer_ids: DF.Table[AdditionalSellerIDs]
        payment_means_type_code: DF.Data | None
        precomputed: DF.Check
        precomputed_invoice: DF.Link | None
        prepayment_id: DF.Data | None
        prepayment_issue_date: DF.Date | None
        prepayment_issue_time: DF.Data | None
        prepayment_type_code: DF.Data | None
        prepayment_uuid: DF.Data | None
        prepayment_vat_category_tax_amount: DF.Float
        prepayment_vat_category_taxable_amount: DF.Float
        previous_invoice_hash: DF.Data | None
        qr_code: DF.SmallText | None
        qr_image_src: DF.Data | None
        reason_for_allowance: DF.Data | None
        reason_for_charge: DF.Data | None
        reason_for_charge_code: DF.Data | None
        sales_invoice: DF.DynamicLink
        sum_of_charges: DF.Float
        supply_end_date: DF.Data | None
        tax_currency: DF.Data | None
        uuid: DF.Data | None
        validation_errors: DF.SmallText | None
        validation_messages: DF.SmallText | None
        vat_exemption_reason_code: DF.Data | None
        vat_exemption_reason_text: DF.SmallText | None
    # end: auto-generated types
    send_mode: ZatcaSendMode = ZatcaSendMode.Production

    @staticmethod
    def create_for_invoice(invoice_id: str,
                           doctype: Literal["Sales Invoice", "POS Invoice"]) -> 'SalesInvoiceAdditionalFields':
        doc = cast(SalesInvoiceAdditionalFields, frappe.new_doc("Sales Invoice Additional Fields"))
        # We do not expect people to create SIAF manually, so nobody has permission to create one
        doc.flags.ignore_permissions = True
        doc.invoice_doctype = doctype
        doc.sales_invoice = invoice_id
        return doc

    @property
    def is_compliance_mode(self) -> bool:
        return self.send_mode == ZatcaSendMode.Compliance

    def use_precomputed_invoice(self, precomputed_invoice: ZATCAPrecomputedInvoice):
        self.precomputed = True
        self.precomputed_invoice = precomputed_invoice.name
        self.invoice_counter = int(precomputed_invoice.invoice_counter)
        self.uuid = precomputed_invoice.invoice_uuid
        self.previous_invoice_hash = precomputed_invoice.previous_invoice_hash
        self.invoice_hash = precomputed_invoice.invoice_hash
        self.invoice_qr = precomputed_invoice.invoice_qr
        self.invoice_xml = precomputed_invoice.invoice_xml

    def _get_invoice_type(self, settings: ZATCABusinessSettings) -> InvoiceType:
        if settings.invoice_mode == InvoiceMode.Standard:
            return 'Standard'

        if settings.invoice_mode == InvoiceMode.Simplified:
            return 'Simplified'

        if self.buyer_vat_registration_number or any([strip(x.value) for x in self.other_buyer_ids]):
            return 'Standard'

        return 'Simplified'

    def before_insert(self):
        self.integration_status = "Ready For Batch"
        self.is_latest = True
        # Mark any pre-existing sales invoice additional fields as no longer being latest
        frappe.db.set_value('Sales Invoice Additional Fields', {'sales_invoice': self.sales_invoice}, 'is_latest', 0)

        if self.precomputed:
            return

        settings = ZATCABusinessSettings.for_invoice(self.sales_invoice, self.invoice_doctype)
        if not settings:
            frappe.throw(f"Missing ZATCA business settings for sales invoice: {self.sales_invoice}")

        sales_invoice = cast(SalesInvoice | POSInvoice, frappe.get_doc(self.invoice_doctype, self.sales_invoice))
        self.uuid = str(uuid.uuid4())
        self.tax_currency = "SAR"  # Review: Set as "SAR" as a default tax currency value

        # FIXME: Buyer details must come before invoice type and code, since this information relies on buyer details
        #   This temporal dependency is not great
        self._set_buyer_details(sales_invoice)
        self.sum_of_charges = self._compute_sum_of_charges(sales_invoice.taxes)
        self.invoice_type_transaction = "0100000" if self._get_invoice_type(settings) == 'Standard' else '0200000'
        self.invoice_type_code = self._get_invoice_type_code(sales_invoice)
        self.payment_means_type_code = self._get_payment_means_type_code(sales_invoice)

        self._prepare_for_zatca(settings)

    def _prepare_for_zatca(self, settings: ZATCABusinessSettings):
        invoice_type = self._get_invoice_type(settings)
        counting_settings_id, pre_invoice_counter, pre_invoice_hash = frappe.db.get_values(
            "ZATCA Invoice Counting Settings", {"business_settings_reference": settings.name},
            ["name", "invoice_counter", "previous_invoice_hash"], for_update=True)[0]

        self.invoice_counter = pre_invoice_counter + 1
        self.previous_invoice_hash = pre_invoice_hash

        einvoice = Einvoice(sales_invoice_additional_fields_doc=self, invoice_type=invoice_type)

        cert_path = settings.compliance_cert_path if self.is_compliance_mode else settings.cert_path
        invoice_xml = generate_xml_file(einvoice.result)
        result = cli.sign_invoice(settings.zatca_cli_path, settings.java_home, invoice_xml, cert_path,
                                  settings.private_key_path)

        if settings.validate_generated_xml and not self.is_compliance_mode:
            validation_result = cli.validate_invoice(settings.zatca_cli_path, settings.java_home,
                                                     result.signed_invoice_path,
                                                     settings.cert_path, self.previous_invoice_hash)
            self.validation_messages = '\n'.join(validation_result.messages)
            self.validation_errors = '\n'.join(validation_result.errors_and_warnings)
            if validation_result.details:
                logger.info(f"Validation Errors: {validation_result.details.errors}")
                logger.info(f"Validation Warnings: {validation_result.details.warnings}")

                # In theory, we shouldn't have an invalid result without errors/warnings, but just in case an unknown
                # error occurs that isn't captured
                is_invalid = ((not validation_result.details.is_valid) or validation_result.details.errors or
                              validation_result.details.warnings)
                if settings.block_invoice_on_invalid_xml and is_invalid:
                    message = f"<h4>{ft('Errors')}</h4>"
                    message += "<ul>"
                    for code, error in validation_result.details.errors.items():
                        message += f"<li><b>{html.escape(code)}</b>: {html.escape(error)}</li>"
                    message += "</ul>"

                    message += f"<h4>{ft('Warnings')}</h4>"
                    message += "<ul>"
                    for code, warning in validation_result.details.warnings.items():
                        message += f"<li><b>{html.escape(code)}</b>: {html.escape(warning)}</li>"
                    message += "</ul>"

                    frappe.throw(title=ft("ZATCA Validation Error"), msg=message)

        self.invoice_hash = result.invoice_hash
        self.qr_code = result.qr_code
        self.invoice_xml = result.signed_invoice_xml

        # To update counting settings data
        logger.info(f"Changing invoice counter, hash from: {pre_invoice_counter}, {pre_invoice_hash} -> "
                    f"{self.invoice_counter}, {self.invoice_hash}")
        frappe.db.set_value("ZATCA Invoice Counting Settings", counting_settings_id, {
            "invoice_counter": self.invoice_counter,
            "previous_invoice_hash": self.invoice_hash
        })

    def submit_to_zatca(self) -> Result[str, str]:
        settings = ZATCABusinessSettings.for_invoice(self.sales_invoice, self.invoice_doctype)
        if not settings:
            return Err(f"Missing ZATCA business settings for sales invoice: {self.sales_invoice}")

        invoice_type = self._get_invoice_type(settings)
        signed_xml = self.get_signed_xml()
        if not signed_xml:
            return Err(_('Could not find signed XML'))

        if self.precomputed_invoice:
            device_id = frappe.db.get_value('ZATCA Precomputed Invoice', self.precomputed_invoice, 'device_id')
            egs = ZATCAEGS.for_device(device_id)
            if not egs:
                return Err(f"Could not find a ZATCA EGS for device '{device_id}'")

            token = egs.production_security_token
            secret = egs.get_password('production_secret') if egs.production_secret else ''
        else:
            token = settings.security_token if self.is_compliance_mode else settings.production_security_token
            secret = settings.get_password('secret' if self.is_compliance_mode else 'production_secret')

        if not token or not secret:
            return Err(f"Missing ZATCA token/secret for {self.name}")

        integration_status = self._send_xml_via_api(signed_xml, self.invoice_hash, invoice_type,
                                                    settings.fatoora_server_url,
                                                    token, secret)

        # Regardless of what happened, save the side effects of the API call
        self.save()

        # Resend means we keep ourselves as draft to be picked up by the next run of the background job
        if integration_status == "Resend":
            frappe.log_error(
                title="ZATCA Resend Error",
                message=f"Sending invoice {self.sales_invoice} through {self.name} failed with 'Resend' status.")
        else:
            # Any case other than resend is submitted
            self.submit()

        return Ok(f"Invoice sent to ZATCA. Integration status: {integration_status}")

    def _get_invoice_type_code(self, invoice_doc: SalesInvoice | POSInvoice) -> str:
        # POSInvoice doesn't have an is_debit_note field
        if invoice_doc.doctype == 'Sales Invoice' and invoice_doc.is_debit_note:
            return "383"

        if invoice_doc.is_return:
            return "381"

        return "388"

    def _get_payment_means_type_code(self, invoice: SalesInvoice | POSInvoice) -> Optional[str]:
        # An invoice can have multiple modes of payment, but we currently only support one. Therefore, we retrieve the
        # first one if any
        if not invoice.payments:
            return None

        mode_of_payment = invoice.payments[0].mode_of_payment
        return frappe.get_value('Mode of Payment', mode_of_payment, 'custom_zatca_payment_means_code')

    def _set_buyer_details(self, sales_invoice: SalesInvoice | POSInvoice):
        customer_doc = cast(Customer, frappe.get_doc("Customer", sales_invoice.customer))

        self.buyer_vat_registration_number = customer_doc.get("custom_vat_registration_number")
        if sales_invoice.customer_address:
            self._set_buyer_address(cast(Address, frappe.get_doc("Address", sales_invoice.customer_address)))

        for item in customer_doc.get("custom_additional_ids"):
            if strip(item.value):
                self.append("other_buyer_ids",
                            {"type_name": item.type_name, "type_code": item.type_code, "value": item.value})

    def _set_buyer_address(self, address: Address):
        self.buyer_additional_number = "not available for now"
        self.buyer_street_name = address.address_line1
        self.buyer_additional_street_name = address.address_line2
        self.buyer_building_number = address.get("custom_building_number")
        self.buyer_city = address.city
        self.buyer_postal_code = address.pincode
        self.buyer_district = address.get("custom_area")
        self.buyer_province_state = address.state
        self.buyer_country_code = frappe.get_value('Country', address.country, 'code')

    def _send_xml_via_api(self, invoice_xml: str, invoice_hash: str, invoice_type: InvoiceType,
                          server_url: str, token: str, secret: str) -> ZatcaIntegrationStatus:
        if invoice_type == 'Standard':
            result, status_code = api.clear_invoice(server=server_url, invoice_xml=invoice_xml,
                                                    invoice_uuid=self.uuid, invoice_hash=invoice_hash,
                                                    security_token=token, secret=secret, mode=self.send_mode)
        else:
            result, status_code = api.report_invoice(server=server_url, invoice_xml=invoice_xml,
                                                     invoice_uuid=self.uuid, invoice_hash=invoice_hash,
                                                     security_token=token, secret=secret, mode=self.send_mode)

        status = ''
        integration_status = _get_integration_status(status_code)
        if is_err(result):
            # The IDE gets confused resolving types, so we help it along
            error = cast(ReportOrClearInvoiceError, result.err_value)
            zatca_message = error.response or error.error
        else:
            value = cast(ReportOrClearInvoiceResult, result.ok_value)
            zatca_message = value.raw_response
            status = value.status

        self._add_integration_log_document(zatca_message=zatca_message, integration_status=integration_status,
                                           zatca_status=status)
        self.integration_status = integration_status
        self.last_attempt = now_datetime()
        return integration_status

    def _compute_sum_of_charges(self, taxes: list) -> float:
        total = 0.0
        if taxes:
            for item in taxes:
                total = total + item.tax_amount
        return total

    def get_signed_xml(self) -> str | None:
        # We leave the attachment logic below intact for backward compatibility. Sales Invoice Additional Fields created
        # before adding the XML field will have the XML as an attachment instead. We may create a patch to migrate them
        # later
        if self.invoice_xml:
            return self.invoice_xml

        attachments = frappe.get_all("File", fields=("name", "file_name", "attached_to_name", "file_url"),
                                     filters={"attached_to_name": self.name,
                                              "attached_to_doctype": "Sales Invoice Additional Fields"})
        if not attachments:
            return None

        name: str | None = None
        for attachment in attachments:
            if attachment.file_name and attachment.file_name.endswith(".xml"):
                name = attachment.name
                break

        if not name:
            return None

        file = cast(File, frappe.get_doc("File", name))
        content = file.get_content()
        if isinstance(content, str):
            return content
        return content.decode('utf-8')

    def _add_integration_log_document(self, zatca_message, integration_status, zatca_status):
        integration_doc = cast(ZATCAIntegrationLog, frappe.get_doc({
            "doctype": "ZATCA Integration Log",
            "invoice_doctype": self.invoice_doctype,
            "invoice_reference": self.sales_invoice,
            "invoice_additional_fields_reference": self.name,
            "zatca_message": zatca_message,
            "status": integration_status,
            "zatca_status": zatca_status,
        }))
        integration_doc.insert(ignore_permissions=True)

    @property
    def qr_image_src(self) -> str | None:
        if not self.qr_code:
            return None
        qr = pyqrcode.create(self.qr_code)
        with BytesIO() as buffer:
            qr.png(buffer, scale=7)
            buffer.seek(0)
            return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("utf-8")

    def before_cancel(self) -> None:
        frappe.throw(msg=_("You cannot cancel sales invoice according to ZATCA Regulations."),
                     title=_("This Action Is Not Allowed"))


@frappe.whitelist()
def download_xml(id: str):
    """
    Frappe doesn't know how to display an XML field without escaping it, so we made the field hidden. The only way
    for users to view the XML is to download it through this endpoint
    """
    siaf = cast(SalesInvoiceAdditionalFields, frappe.get_doc('Sales Invoice Additional Fields', id))

    # Reference: https://frappeframework.com/docs/user/en/python-api/response
    frappe.response.filename = siaf.name + '.xml'
    frappe.response.filecontent = siaf.get_signed_xml()
    frappe.response.type = "download"
    frappe.response.display_content_as = "attachment"


@frappe.whitelist()
def fix_rejection(id: str):
    import frappe.permissions
    if not frappe.permissions.has_permission('Sales Invoice Additional Fields'):
        raise PermissionError()

    siaf = cast(SalesInvoiceAdditionalFields, frappe.get_doc('Sales Invoice Additional Fields', id))
    if siaf.precomputed_invoice:
        frappe.throw(ft("Cannot fix rejection for a precomputed invoice from Desk"))

    if not siaf.is_latest:
        frappe.throw(ft("This is not the latest Sales Invoice Additional Fields for invoice $invoice. Please fix "
                        "rejection from the latest", invoice=siaf.sales_invoice))

    settings = ZATCABusinessSettings.for_invoice(siaf.sales_invoice, siaf.invoice_doctype)
    if not settings:
        frappe.throw(ft("Missing ZATCA business settings for sales invoice: $invoice", invoice=siaf.sales_invoice))

    new_siaf = SalesInvoiceAdditionalFields.create_for_invoice(siaf.sales_invoice, siaf.invoice_doctype)
    new_siaf.insert()

    if settings.is_live_sync:
        frappe.utils.background_jobs.enqueue(_submit_additional_fields, doc=new_siaf, enqueue_after_commit=True)

    frappe.msgprint(ft("Created $link", link=get_link_to_form("Sales Invoice Additional Fields", new_siaf.name)))


def _get_integration_status(code: int) -> ZatcaIntegrationStatus:
    status_map = cast(dict[int, ZatcaIntegrationStatus], {
        200: "Accepted",
        202: "Accepted with warnings",
        303: "Clearance switched off",
        401: "Rejected",
        400: "Rejected",
        413: "Resend",
        429: "Resend",
        500: "Resend",
        503: "Resend",
        504: "Resend"
    })
    if code and code in status_map:
        return status_map[code]
    else:
        return "Resend"


def _submit_additional_fields(doc: SalesInvoiceAdditionalFields):
    logger.info(f'Submitting {doc.name}')
    result = doc.submit_to_zatca()
    message = result.ok_value if is_ok(result) else result.err_value
    logger.info(f'Submission result: {message}')
