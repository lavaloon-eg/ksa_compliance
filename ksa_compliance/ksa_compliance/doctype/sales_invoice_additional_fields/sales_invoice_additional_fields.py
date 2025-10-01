# Copyright (c) 2024, Lavaloon and contributors
# For license information, please see license.txt
from __future__ import annotations

import base64
import html
import uuid
from io import BytesIO
from typing import cast, Optional, Literal
from ksa_compliance import SALES_INVOICE_CODE, DEBIT_NOTE_CODE, CREDIT_NOTE_CODE, PREPAYMENT_INVOICE_CODE
import frappe
import frappe.utils.background_jobs
import pyqrcode
from erpnext.accounts.doctype.pos_invoice.pos_invoice import POSInvoice
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
from erpnext.selling.doctype.customer.customer import Customer
from frappe import _
from frappe.contacts.doctype.address.address import Address
from frappe.core.doctype.file.file import File
from frappe.model.document import Document
from frappe.translate import print_language
from frappe.utils import now_datetime, get_link_to_form, strip, get_url
from frappe.utils.pdf import get_file_data_from_writer
from pypdf import PdfWriter
from result import is_err, Result, Err, Ok, is_ok

from ksa_compliance import logger
from ksa_compliance import zatca_api as api
from ksa_compliance import zatca_cli as cli
from ksa_compliance.generate_xml import generate_xml_file
from ksa_compliance.invoice import InvoiceMode, InvoiceType
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings
from ksa_compliance.ksa_compliance.doctype.zatca_egs.zatca_egs import ZATCAEGS
from ksa_compliance.ksa_compliance.doctype.zatca_integration_log.zatca_integration_log import ZATCAIntegrationLog
from ksa_compliance.ksa_compliance.doctype.zatca_precomputed_invoice.zatca_precomputed_invoice import (
    ZATCAPrecomputedInvoice,
)
from ksa_compliance.output_models.e_invoice_output_model import Einvoice
from ksa_compliance.translation import ft
from ksa_compliance.throw import fthrow
from ksa_compliance.zatca_api import ReportOrClearInvoiceError, ReportOrClearInvoiceResult, ZatcaSendMode
from ksa_compliance.zatca_cli import convert_to_pdf_a3_b, check_pdfa3b_support_or_throw

# These are the possible statuses resulting from a submission to ZATCA. Note that this is a subset of
# [SalesInvoiceAdditionalFields.integration_status]
ZatcaIntegrationStatus = Literal[
    'Resend', 'Accepted with warnings', 'Accepted', 'Rejected', 'Clearance switched off', 'Duplicate'
]


class SalesInvoiceAdditionalFields(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from ksa_compliance.ksa_compliance.doctype.additional_seller_ids.additional_seller_ids import (
            AdditionalSellerIDs,
        )

        allow_submit: DF.Check
        allowance_indicator: DF.Check
        allowance_vat_category_code: DF.Data | None
        amended_from: DF.Link | None
        branch: DF.Link | None
        branch_commercial_registration_number: DF.Data | None
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
        integration_status: DF.Literal[
            '',
            'Ready For Batch',
            'Resend',
            'Corrected',
            'Accepted with warnings',
            'Accepted',
            'Rejected',
            'Clearance switched off',
            'Duplicate',
        ]
        invoice_counter: DF.Int
        invoice_doctype: DF.Literal['Sales Invoice', 'POS Invoice', 'Payment Entry']
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
    def create_for_invoice(
        invoice_id: str, doctype: Literal['Sales Invoice', 'POS Invoice', 'Payment Entry']
    ) -> 'SalesInvoiceAdditionalFields':
        doc = cast(SalesInvoiceAdditionalFields, frappe.new_doc('Sales Invoice Additional Fields'))
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

    def _get_invoice_type(self, settings: ZATCABusinessSettings, customer: Customer) -> InvoiceType:
        if settings.invoice_mode == InvoiceMode.Standard:
            return 'Standard'

        if settings.invoice_mode == InvoiceMode.Simplified:
            return 'Simplified'

        if is_b2b_customer(customer):
            return 'Standard'

        return 'Simplified'

    def before_insert(self):
        self.integration_status = 'Ready For Batch'
        self.is_latest = True
        # Mark any pre-existing sales invoice additional fields as no longer being latest
        frappe.db.set_value('Sales Invoice Additional Fields', {'sales_invoice': self.sales_invoice}, 'is_latest', 0)

        if self.precomputed:
            return

        settings = ZATCABusinessSettings.for_invoice(self.sales_invoice, self.invoice_doctype)
        if not settings:
            frappe.throw(f'Missing ZATCA business settings for sales invoice: {self.sales_invoice}')

        sales_invoice = cast(
            SalesInvoice | POSInvoice | PaymentEntry, frappe.get_doc(self.invoice_doctype, self.sales_invoice)
        )
        self.uuid = str(uuid.uuid4())
        self.tax_currency = 'SAR'  # Review: Set as "SAR" as a default tax currency value

        buyer_doc = self._get_buyer_doc(sales_invoice)
        invoice_type = self._get_invoice_type(settings, buyer_doc)
        self._set_buyer_details(buyer_doc, invoice_type)
        self.sum_of_charges = self._compute_sum_of_charges(sales_invoice.taxes)
        self.invoice_type_transaction = '0100000' if invoice_type == 'Standard' else '0200000'
        self.invoice_type_code = self._get_invoice_type_code(sales_invoice)
        self.payment_means_type_code = self._get_payment_means_type_code(sales_invoice)

        if settings.enable_branch_configuration:
            self._set_branch_details(sales_invoice)

        self._prepare_for_zatca(settings, invoice_type)

    def _prepare_for_zatca(self, settings: ZATCABusinessSettings, invoice_type: InvoiceType):
        counting_settings_id, pre_invoice_counter, pre_invoice_hash = frappe.db.get_values(
            'ZATCA Invoice Counting Settings',
            {'business_settings_reference': settings.name},
            ['name', 'invoice_counter', 'previous_invoice_hash'],
            for_update=True,
        )[0]

        self.invoice_counter = pre_invoice_counter + 1
        self.previous_invoice_hash = pre_invoice_hash

        einvoice = Einvoice(sales_invoice_additional_fields_doc=self, invoice_type=invoice_type)

        cert_path = settings.compliance_cert_path if self.is_compliance_mode else settings.cert_path
        invoice_xml = generate_xml_file(einvoice.result)
        result = cli.sign_invoice(
            settings.zatca_cli_path, settings.java_home, invoice_xml, cert_path, settings.private_key_path
        )

        if settings.validate_generated_xml and not self.is_compliance_mode:
            validation_result = cli.validate_invoice(
                settings.zatca_cli_path,
                settings.java_home,
                result.signed_invoice_path,
                settings.cert_path,
                self.previous_invoice_hash,
            )
            self.validation_messages = '\n'.join(validation_result.messages)
            self.validation_errors = '\n'.join(validation_result.errors_and_warnings)
            if validation_result.details:
                logger.info(f'Validation Errors: {validation_result.details.errors}')
                logger.info(f'Validation Warnings: {validation_result.details.warnings}')

                # In theory, we shouldn't have an invalid result without errors/warnings, but just in case an unknown
                # error occurs that isn't captured
                is_invalid = (
                    (not validation_result.details.is_valid)
                    or validation_result.details.errors
                    or validation_result.details.warnings
                )
                if settings.block_invoice_on_invalid_xml and is_invalid:
                    html_message = ''
                    text_message = ''
                    if validation_result.details.errors:
                        text_message += ft('Errors') + '\n'
                        html_message += f"<h4>{ft('Errors')}</h4>"
                        html_message += '<ul>'
                        for code, error in validation_result.details.errors.items():
                            html_message += f'<li><b>{html.escape(code)}</b>: {html.escape(error)}</li>'
                            text_message += f'{code}: {error}\n'
                        html_message += '</ul>'

                    if validation_result.details.warnings:
                        text_message += ft('Warnings') + '\n'
                        html_message += f"<h4>{ft('Warnings')}</h4>"
                        html_message += '<ul>'
                        for code, warning in validation_result.details.warnings.items():
                            html_message += f'<li><b>{html.escape(code)}</b>: {html.escape(warning)}</li>'
                            text_message += f'{code}: {warning}\n'
                        html_message += '</ul>'

                    frappe.log_error(
                        title=ft('ZATCA Validation Error'),
                        message=text_message + '\n\n' + invoice_xml,
                        reference_doctype=self.invoice_doctype,
                        reference_name=self.sales_invoice,
                    )
                    frappe.throw(title=ft('ZATCA Validation Error'), msg=html_message)

        self.invoice_hash = result.invoice_hash
        self.qr_code = result.qr_code
        self.invoice_xml = result.signed_invoice_xml

        # To update counting settings data
        logger.info(
            f'Changing invoice counter, hash from: {pre_invoice_counter}, {pre_invoice_hash} -> '
            f'{self.invoice_counter}, {self.invoice_hash}'
        )
        frappe.db.set_value(
            'ZATCA Invoice Counting Settings',
            counting_settings_id,
            {'invoice_counter': self.invoice_counter, 'previous_invoice_hash': self.invoice_hash},
        )

    def submit_to_zatca(self) -> Result[str, str]:
        settings = ZATCABusinessSettings.for_invoice(self.sales_invoice, self.invoice_doctype)
        if not settings:
            return Err(f'Missing ZATCA business settings for sales invoice: {self.sales_invoice}')

        inv_doc = cast(
            SalesInvoice | POSInvoice | PaymentEntry, frappe.get_doc(self.invoice_doctype, self.sales_invoice)
        )
        buyer_doc = self._get_buyer_doc(inv_doc)
        invoice_type = self._get_invoice_type(settings, buyer_doc)
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
            return Err(f'Missing ZATCA token/secret for {self.name}')

        integration_status = self._send_xml_via_api(
            signed_xml, self.invoice_hash, invoice_type, settings.fatoora_server_url, token, secret
        )

        # Regardless of what happened, save the side effects of the API call
        self.save()

        # Resend means we keep ourselves as draft to be picked up by the next run of the background job
        if integration_status == 'Resend':
            frappe.log_error(
                title='ZATCA Resend Error',
                message=f"Sending invoice {self.sales_invoice} through {self.name} failed with 'Resend' status.",
            )
        else:
            # Any case other than resend is submitted
            self.allow_submit = 1
            self.submit()

        return Ok(f'Invoice sent to ZATCA. Integration status: {integration_status}')

    def before_submit(self):
        if not self.allow_submit:
            sync_invoices_url = get_url(uri='/app/e-invoicing-sync')
            sync_invoices_page = f'<a href="{sync_invoices_url}">{ft("Sync Invoices Page")}</a>'
            fthrow(
                msg=ft(
                    'You cannot submit SIAF manually; if you want to resubmit it to ZATCA use $sync_invoices_page',
                    sync_invoices_page=sync_invoices_page,
                ),
                title=ft('Validation Error'),
            )

    def _get_invoice_type_code(self, invoice_doc: SalesInvoice | POSInvoice | PaymentEntry) -> str:
        # POSInvoice doesn't have an is_debit_note field
        if invoice_doc.doctype == 'Payment Entry' and invoice_doc.custom_prepayment_invoice:
            return str(PREPAYMENT_INVOICE_CODE)
        if invoice_doc.doctype == 'Sales Invoice' and invoice_doc.is_debit_note:
            return str(DEBIT_NOTE_CODE)
        if invoice_doc.is_return:
            return str(CREDIT_NOTE_CODE)
        return str(SALES_INVOICE_CODE)

    def _get_payment_means_type_code(self, invoice: SalesInvoice | POSInvoice | PaymentEntry) -> Optional[str]:
        if invoice.doctype == 'Payment Entry':
            return frappe.get_value('Mode of Payment', invoice.mode_of_payment, 'custom_zatca_payment_means_code')

        # An invoice can have multiple modes of payment, but we currently only support one. Therefore, we retrieve the
        # first one if any
        if not invoice.payments:
            return None
        mode_of_payment = invoice.payments[0].mode_of_payment
        return frappe.get_value('Mode of Payment', mode_of_payment, 'custom_zatca_payment_means_code')

    def _get_buyer_doc(
        self,
        sales_invoice: SalesInvoice | POSInvoice | PaymentEntry = None,
    ) -> Customer:
        if sales_invoice.doctype == 'Payment Entry':
            customer_name = sales_invoice.party
        else:
            customer_name = sales_invoice.customer
        return cast(Customer, frappe.get_doc('Customer', customer_name))

    def _set_buyer_details(self, customer: Customer, invoice_type: InvoiceType):
        self.buyer_vat_registration_number = customer.get('custom_vat_registration_number')
        _is_b2b_customer = invoice_type == 'Standard'
        if customer.customer_primary_address:
            address_doc = cast(Address, frappe.get_doc('Address', customer.customer_primary_address))
            self._set_buyer_address(address_doc, _is_b2b_customer)
        else:
            address = frappe.db.get_all(
                'Dynamic Link',
                {
                    'parenttype': 'Address',
                    'parentfield': 'links',
                    'link_doctype': 'Customer',
                    'link_name': customer.name,
                },
                pluck='parent',
            )
            if address:
                address_doc = cast(Address, frappe.get_doc('Address', address[0]))
                self._set_buyer_address(address_doc, _is_b2b_customer)
            else:
                if _is_b2b_customer:
                    customer_form = frappe.utils.get_link_to_form('Customer', customer.name)
                    fthrow(
                        ft(
                            'Customer address is mandatory for B2B transactions; Please set a customer address for B2B customer $customer.',
                            customer=customer_form,
                        ),
                        title=ft('Address Not Found Error'),
                    )

        for item in customer.get('custom_additional_ids'):
            if strip(item.value):
                self.append(
                    'other_buyer_ids', {'type_name': item.type_name, 'type_code': item.type_code, 'value': item.value}
                )

    def _set_buyer_address(self, address: Address, validate: bool = False):
        if validate:
            self.validate_buyer_address(address)
        self.buyer_additional_number = 'not available for now'
        self.buyer_street_name = address.address_line1
        self.buyer_additional_street_name = address.address_line2
        self.buyer_building_number = address.get('custom_building_number')
        self.buyer_city = address.city
        self.buyer_postal_code = address.pincode
        self.buyer_district = address.get('custom_area')
        self.buyer_province_state = address.state
        self.buyer_country_code = frappe.get_value('Country', address.country, 'code')

    def _send_xml_via_api(
        self, invoice_xml: str, invoice_hash: str, invoice_type: InvoiceType, server_url: str, token: str, secret: str
    ) -> ZatcaIntegrationStatus:
        if invoice_type == 'Standard':
            result, status_code = api.clear_invoice(
                server=server_url,
                invoice_xml=invoice_xml,
                invoice_uuid=self.uuid,
                invoice_hash=invoice_hash,
                security_token=token,
                secret=secret,
                mode=self.send_mode,
            )
        else:
            result, status_code = api.report_invoice(
                server=server_url,
                invoice_xml=invoice_xml,
                invoice_uuid=self.uuid,
                invoice_hash=invoice_hash,
                security_token=token,
                secret=secret,
                mode=self.send_mode,
            )

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

        self._add_integration_log_document(
            zatca_message=zatca_message,
            integration_status=integration_status,
            zatca_status=status,
            status_code=status_code,
        )
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

        attachments = frappe.get_all(
            'File',
            fields=('name', 'file_name', 'attached_to_name', 'file_url'),
            filters={'attached_to_name': self.name, 'attached_to_doctype': 'Sales Invoice Additional Fields'},
        )
        if not attachments:
            return None

        name: str | None = None
        for attachment in attachments:
            if attachment.file_name and attachment.file_name.endswith('.xml'):
                name = attachment.name
                break

        if not name:
            return None

        file = cast(File, frappe.get_doc('File', name))
        content = file.get_content()
        if isinstance(content, str):
            return content
        return content.decode('utf-8')

    def _add_integration_log_document(
        self, zatca_message: Optional[str], integration_status: str, zatca_status: Optional[str], status_code: int
    ):
        integration_doc = cast(
            ZATCAIntegrationLog,
            frappe.get_doc(
                {
                    'doctype': 'ZATCA Integration Log',
                    'invoice_doctype': self.invoice_doctype,
                    'invoice_reference': self.sales_invoice,
                    'invoice_additional_fields_reference': self.name,
                    'zatca_message': zatca_message,
                    'status': integration_status,
                    'zatca_status': zatca_status,
                    'zatca_http_status_code': status_code,
                }
            ),
        )
        integration_doc.insert(ignore_permissions=True)

    def _set_branch_details(self, invoice: SalesInvoice | POSInvoice | PaymentEntry):
        if invoice.branch:
            self.branch = invoice.branch
            self.branch_commercial_registration_number = frappe.get_value(
                'Additional Seller IDs',
                {
                    'parent': self.branch,
                    'parenttype': 'Branch',
                    'parentfield': 'custom_branch_ids',
                    'type_code': 'CRN',
                },
                'value',
            )

    @property
    def qr_image_src(self) -> str | None:
        if not self.qr_code:
            return None
        qr = pyqrcode.create(self.qr_code)
        with BytesIO() as buffer:
            qr.png(buffer, scale=7)
            buffer.seek(0)
            return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode('utf-8')

    def before_cancel(self) -> None:
        frappe.throw(
            msg=_('You cannot cancel sales invoice according to ZATCA Regulations.'),
            title=_('This Action Is Not Allowed'),
        )

    @staticmethod
    def validate_buyer_address(address: Address):
        msg_list = []
        if not address.address_line1:
            msg = _('Please set Address Line 1 for customer address.')
            msg_list.append(msg)

        if not address.get('custom_building_number') or len(address.get('custom_building_number')) != 4:
            msg = _('Please make sure that building number is set and is 4 digits exactly in customer address.')
            msg_list.append(msg)

        if not address.city:
            msg = _('Please set city for customer address.')
            msg_list.append(msg)

        if not address.pincode or len(address.pincode) != 5:
            msg = _('Please make sure that postal code is set and is 5 digits exactly in customer address.')
            msg_list.append(msg)

        if not address.get('custom_area'):
            msg = _('Please set district for customer address.')
            msg_list.append(msg)

        if msg_list:
            msg_list.append(frappe.utils.get_link_to_form('Address', address.name, _('Update Address')))
            message = '<hr>'.join(msg_list)
            fthrow(
                msg=message,
                title=_('Invalid Address Error'),
            )


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
    frappe.response.type = 'download'
    frappe.response.display_content_as = 'attachment'


@frappe.whitelist()
def fix_rejection(id: str):
    import frappe.permissions

    if not frappe.permissions.has_permission('Sales Invoice Additional Fields'):
        raise PermissionError()

    siaf = cast(SalesInvoiceAdditionalFields, frappe.get_doc('Sales Invoice Additional Fields', id))
    if siaf.precomputed_invoice:
        frappe.throw(ft('Cannot fix rejection for a precomputed invoice from Desk'))

    if not siaf.is_latest:
        frappe.throw(
            ft(
                'This is not the latest Sales Invoice Additional Fields for invoice $invoice. Please fix '
                'rejection from the latest',
                invoice=siaf.sales_invoice,
            )
        )

    settings = ZATCABusinessSettings.for_invoice(siaf.sales_invoice, siaf.invoice_doctype)
    if not settings:
        frappe.throw(ft('Missing ZATCA business settings for sales invoice: $invoice', invoice=siaf.sales_invoice))

    new_siaf = SalesInvoiceAdditionalFields.create_for_invoice(siaf.sales_invoice, siaf.invoice_doctype)
    new_siaf.insert()

    if settings.is_live_sync:
        frappe.utils.background_jobs.enqueue(_submit_additional_fields, doc=new_siaf, enqueue_after_commit=True)

    frappe.msgprint(ft('Created $link', link=get_link_to_form('Sales Invoice Additional Fields', new_siaf.name)))


def _get_integration_status(code: int) -> ZatcaIntegrationStatus:
    status_map = cast(
        dict[int, ZatcaIntegrationStatus],
        {
            200: 'Accepted',
            202: 'Accepted with warnings',
            208: 'Duplicate',
            303: 'Clearance switched off',
            401: 'Rejected',
            400: 'Rejected',
            413: 'Resend',
            429: 'Resend',
            500: 'Resend',
            503: 'Resend',
            504: 'Resend',
        },
    )
    if code and code in status_map:
        return status_map[code]
    elif code and 200 <= code < 300:
        return 'Accepted'
    else:
        return 'Resend'


def _submit_additional_fields(doc: SalesInvoiceAdditionalFields):
    logger.info(f'Submitting {doc.name}')
    result = doc.submit_to_zatca()
    message = result.ok_value if is_ok(result) else result.err_value
    logger.info(f'Submission result: {message}')


@frappe.whitelist()
def check_pdf_a3b_support(id: str):
    siaf = cast(SalesInvoiceAdditionalFields, frappe.get_doc('Sales Invoice Additional Fields', id))
    settings = ZATCABusinessSettings.for_invoice(siaf.sales_invoice, siaf.invoice_doctype)
    check_pdfa3b_support_or_throw(settings.zatca_cli_path, settings.java_home)


@frappe.whitelist()
def download_zatca_pdf(id: str, print_format: str = 'ZATCA Phase 2 Print Format', lang: str = 'en'):
    siaf = cast(SalesInvoiceAdditionalFields, frappe.get_doc('Sales Invoice Additional Fields', id))
    sales_invoice_doc = cast(SalesInvoice, frappe.get_doc('Sales Invoice', siaf.sales_invoice))
    settings = ZATCABusinessSettings.for_invoice(siaf.sales_invoice, siaf.invoice_doctype)
    xml_content = siaf.get_signed_xml()
    pdf_writer = PdfWriter()
    pdf_writer.add_metadata(
        {
            '/Author': settings.company,
            '/Title': siaf.sales_invoice,
            '/Subject': siaf.sales_invoice,
        }
    )
    with print_language(lang):
        frappe.get_print(
            'Sales Invoice',
            siaf.sales_invoice,
            print_format,
            doc=sales_invoice_doc,
            as_pdf=True,
            output=pdf_writer,
        )
    pdf_file = get_file_data_from_writer(pdf_writer)

    zatca_pdf_path = convert_to_pdf_a3_b(
        settings.zatca_cli_path, settings.java_home, siaf.sales_invoice, pdf_file, xml_content
    )

    with open(zatca_pdf_path, 'rb') as f:
        pdf_content = f.read()

    frappe.response.filename = f'{siaf.sales_invoice}_a3b.pdf'
    frappe.response.filecontent = pdf_content
    frappe.response.type = 'download'
    frappe.response.display_content_as = 'attachment'


def is_b2b_customer(customer: Customer) -> bool:
    return bool(customer.custom_vat_registration_number) or any(
        [strip(x.value) for x in customer.custom_additional_ids]
    )


@frappe.whitelist()
def get_zatca_integration_status(invoice_id: str, doctype: Literal['Sales Invoice', 'POS Invoice', 'Payment Entry']):
    integration_status = frappe.db.get_value(
        'Sales Invoice Additional Fields',
        {'sales_invoice': invoice_id, 'invoice_doctype': doctype, 'is_latest': 1},
        'integration_status',
    )

    frappe.response['integration_status'] = integration_status or ''
