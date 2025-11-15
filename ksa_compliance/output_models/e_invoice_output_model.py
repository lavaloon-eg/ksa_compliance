from __future__ import annotations

from typing import cast, Optional, List

import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
from erpnext.setup.doctype.branch.branch import Branch
from frappe.model.document import Document
from frappe.utils import get_date_str, get_time, strip
from ksa_compliance.invoice import InvoiceType, get_zatca_discount_reason_by_name
from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields import sales_invoice_additional_fields
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings
from ksa_compliance.ksa_compliance.doctype.zatca_return_against_reference.zatca_return_against_reference import (
    ZATCAReturnAgainstReference,
)
from ksa_compliance.throw import fthrow
from ksa_compliance.translation import ft
from frappe.utils import flt

from .service import get_right_fieldname, update_result
from .prepayment_invoice.prepayment_invoice_factory import prepayment_invoice_factory_create

from .tax import create_tax_categories, create_allowance_charge, create_tax_total


class Einvoice:
    def __init__(
        self,
        sales_invoice_additional_fields_doc: 'sales_invoice_additional_fields.SalesInvoiceAdditionalFields',
        invoice_type: InvoiceType = 'Simplified',
    ):
        self.additional_fields_doc = sales_invoice_additional_fields_doc
        self.result = {
            'invoice': {},
            'business_settings': {},
            'seller_details': {},
            'buyer_details': {},
            'prepayment_invoice': {},
        }

        self.sales_invoice_doc = cast(
            SalesInvoice | PaymentEntry,
            frappe.get_doc(
                sales_invoice_additional_fields_doc.invoice_doctype, sales_invoice_additional_fields_doc.sales_invoice
            ),
        )
        self.business_settings_doc = ZATCABusinessSettings.for_invoice(
            self.sales_invoice_doc.name, sales_invoice_additional_fields_doc.invoice_doctype
        )

        self.branch_doc = None
        if self.business_settings_doc.enable_branch_configuration:
            if not self.sales_invoice_doc.branch:
                fthrow(
                    msg=ft('Branch is mandatory when ZATCA Branch configuration is enabled.'),
                    title=ft('Branch Is Mandatory'),
                )

            self.branch_doc = cast(
                Branch,
                frappe.get_doc(
                    'Branch',
                    self.sales_invoice_doc.branch,
                ),
            )
            if self.branch_doc.custom_company != self.sales_invoice_doc.company:
                fthrow(
                    msg=ft(
                        'Selected branch $branch is not configured for company: $company.',
                        branch=self.sales_invoice_doc.branch,
                        company=self.sales_invoice_doc.company,
                    ),
                    title=ft('Invalid Branch For Company'),
                )

        # Get Business Settings and Seller Fields
        self.get_business_settings_and_seller_details()

        # Get Buyer Fields
        self.get_buyer_details()

        # Get E-Invoice Fields

        # TODO: Delivery (Supply start and end dates)
        # TODO: Allowance Charge (Discount)
        # FIXME: IF invoice is pre-paid
        self.get_text_value(
            field_name='payment_means_type_code',
            source_doc=self.additional_fields_doc,
            xml_name='payment_means_type_code',
            parent='invoice',
        )

        if self.sales_invoice_doc.get('is_debit_note') or self.sales_invoice_doc.get('is_return'):
            if self.sales_invoice_doc.doctype == 'Sales Invoice':
                self.get_text_value(
                    field_name='custom_return_reason',
                    source_doc=self.sales_invoice_doc,
                    xml_name='instruction_note',
                    parent='invoice',
                )
            else:
                self.set_value('invoice', 'instruction_note', 'Return of goods')

        self.get_text_value(
            field_name='mode_of_payment', source_doc=self.sales_invoice_doc, xml_name='PaymentNote', parent='invoice'
        )

        self.get_text_value(
            field_name='payment_account_identifier', source_doc=self.sales_invoice_doc, xml_name='ID', parent='invoice'
        )

        # <----- start document level allowance ----->
        # fields from 49 to 58  document level allowance
        self.get_float_value(
            field_name='document_level_allowance_percentage',
            source_doc=self.additional_fields_doc,
            xml_name='charge_indicator',
            parent='invoice',
        )

        self.get_float_value(
            field_name='document_level_allowance_amount',
            source_doc=self.additional_fields_doc,
            xml_name='amount',
            parent='invoice',
        )

        self.get_float_value(
            field_name='document_level_allowance_base_amount',
            source_doc=self.additional_fields_doc,
            xml_name='amount',
            parent='invoice',
        )

        self.get_text_value(
            field_name='document_level_allowance_vat_category_code',
            source_doc=self.additional_fields_doc,
            xml_name='ID',
            parent='invoice',
        )

        self.get_float_value(
            field_name='document_level_allowance_vat_rate',
            source_doc=self.additional_fields_doc,
            xml_name='percent',
            parent='invoice',
        )

        # Allowance on invoice should be only the document level allowance without items allowances.
        # Note: allowance_total_amount is now calculated from actual allowance_charge list (see get_e_invoice_details)
        # to ensure BR-CO-11 compliance (sum of allowances must match AllowanceTotalAmount exactly)
        # self.get_float_value(
        #     field_name='discount_amount',
        #     source_doc=self.sales_invoice_doc,
        #     xml_name='allowance_total_amount',
        #     parent='invoice',
        # )
        # self.compute_invoice_discount_amount()
        self.get_e_invoice_details(invoice_type)

        # <----- end document level allowance ----->

        # Fields from 62 : 71 document level charge
        # <----- start document level charge ----->

        self.get_bool_value(
            field_name='charge_indicator',
            source_doc=self.additional_fields_doc,
            xml_name='charge_indicator',
            parent='invoice',
        )

        self.get_float_value(
            field_name='charge_percentage',
            source_doc=self.additional_fields_doc,
            xml_name='MultiplierFactorNumeric',
            parent='invoice',
        )

        self.get_float_value(
            field_name='charge_amount', source_doc=self.additional_fields_doc, xml_name='amount', parent='invoice'
        )

        self.get_float_value(
            field_name='charge_base_amount',
            source_doc=self.additional_fields_doc,
            xml_name='base_amount',
            parent='invoice',
        )

        self.get_text_value(
            field_name='charge_vat_category_code',
            source_doc=self.additional_fields_doc,
            xml_name='ID',
            parent='invoice',
        )

        self.get_float_value(
            field_name='charge_vat_rate', source_doc=self.additional_fields_doc, xml_name='Percent', parent='invoice'
        )

        self.get_text_value(
            field_name='reason_for_charge',
            source_doc=self.additional_fields_doc,
            xml_name='reason_for_charge',
            parent='invoice',
        )

        self.get_text_value(
            field_name='reason_for_charge_code',
            source_doc=self.additional_fields_doc,
            xml_name='reason_for_charge_code',
            parent='invoice',
        )

        # <----- end document level charge ----->
        self.get_float_value(
            field_name='sum_of_charges',
            source_doc=self.additional_fields_doc,
            xml_name='charge_total_amount',
            parent='invoice',
        )

        # Invoice Line
        self.get_bool_value(
            field_name='invoice_line_allowance_indicator',
            source_doc=self.additional_fields_doc,
            xml_name='ID',
            parent='invoice',
        )

        self.get_float_value(
            field_name='invoice_line_allowance_percentage',
            source_doc=self.additional_fields_doc,
            xml_name='multiplier_factor_numeric',
            parent='invoice',
        )

        # TODO: Add Conditional Case
        self.get_float_value(
            field_name='invoice_line_charge_amount',
            source_doc=self.additional_fields_doc,
            xml_name='MultiplierFactorNumeric',
            parent='invoice',
        )

    # --------------------------- START helper functions ------------------------------

    def get_text_value(self, field_name: str, source_doc: Document, xml_name: str = None, parent: str = None):
        field_value = (
            source_doc.get(get_right_fieldname(field_name, source_doc.doctype)).strip()
            if source_doc.get(get_right_fieldname(field_name, source_doc.doctype))
            else None
        )

        if field_value is None:
            return

        field_name = xml_name if xml_name else field_name
        return self.set_value(parent, field_name, field_value)

    # This is a transitional method without all the obsolete validation/rules boilerplate
    def set_value(self, parent: Optional[str], field_name: str, field_value: any):
        if parent:
            if self.result.get(parent):
                self.result[parent][field_name] = field_value
            else:
                self.result[parent] = {}
                self.result[parent][field_name] = field_value

        return field_value

    def get_bool_value(self, field_name: str, source_doc: Document, xml_name: str = None, parent: str = None):
        field_value = source_doc.get(field_name) if source_doc.get(field_name) else None
        if field_value is None:
            return

        field_name = xml_name if xml_name else field_name
        if parent:
            if self.result.get(parent):
                self.result[parent][field_name] = field_value
            else:
                self.result[parent] = {}
                self.result[parent][field_name] = field_value

        return field_value

    def get_int_value(self, field_name: str, source_doc: Document, xml_name: str = None, parent: str = None):
        field_value = cast(any, source_doc.get(field_name, None))

        if field_value is None:
            return
        field_value = int(field_value)
        # Review: This 'abs' is questionable. It was added as part of credit note support, presumably to prevent
        # negative quantities and monetary values (total, price, etc.) but it should've been added on a case-by-case
        # basis
        field_value = abs(field_value)

        field_name = xml_name if xml_name else field_name
        if parent:
            if self.result.get(parent):
                self.result[parent][field_name] = field_value
            else:
                self.result[parent] = {}
                self.result[parent][field_name] = field_value
        return field_value

    def get_float_value(self, field_name: str, source_doc: Document, xml_name: str = None, parent: str = None) -> float:
        field_value = cast(any, source_doc.get(get_right_fieldname(field_name, source_doc.doctype)))

        if field_value is None:
            return 0.0

        field_value = float(field_value) if type(field_value) is int else field_value
        # Review: This 'abs' is questionable. It was added as part of credit note support, presumably to prevent
        # negative quantities and monetary values (total, price, etc.) but it should've been added on a case-by-case
        # basis
        field_value = abs(field_value)

        field_name = xml_name if xml_name else field_name
        if parent:
            if self.result.get(parent):
                self.result[parent][field_name] = field_value
            else:
                self.result[parent] = {}
                self.result[parent][field_name] = field_value
        return field_value

    def get_date_value(self, field_name, source_doc, xml_name, parent):
        field_value = source_doc.get(field_name, None)
        if field_value is None:
            return

        # Try to parse
        field_value = get_date_str(field_value)

        field_name = xml_name if xml_name else field_name
        if parent:
            if self.result.get(parent):
                self.result[parent][field_name] = field_value
            else:
                self.result[parent] = {}
                self.result[parent][field_name] = field_value
        return field_value

    def get_time_value(self, field_name, source_doc, xml_name, parent) -> str | None:
        field_value = source_doc.get(get_right_fieldname(field_name, source_doc.doctype), None)

        if not field_value:
            return

        # We can't use frappe.utils.get_time_str because it results in invalid formats if any component is
        # single-digit, e.g. 00:04:05 is represented as 0:4:5. ZATCA tries to parse an ISO date/time format
        # created from the date and time joined with a T (e.g. 2024-02-20T00:04:05), and it fails to parse the
        # format produced by get_time_str
        formatted_value = get_time(field_value).strftime('%H:%M:%S')

        field_name = xml_name if xml_name else field_name
        if parent:
            if self.result.get(parent):
                self.result[parent][field_name] = formatted_value
            else:
                self.result[parent] = {}
                self.result[parent][field_name] = formatted_value
        return formatted_value

    def get_list_value(self, field_name: str, source_doc: Document, xml_name: str = None, parent: str = None):
        field_value = source_doc.get(field_name)
        if field_value is None or {}:
            return

        if xml_name == 'party_identifications':
            if parent == 'seller_details':
                party_list = ['CRN', 'MOM', 'MLS', '700', 'SAG', 'OTH']
            else:  # buyer_details
                party_list = ['TIN', 'CRN', 'MOM', 'MLS', '700', 'SAG', 'NAT', 'GCC', 'IQA', 'PAS', 'OTH']
            if field_value:
                field_value = self.validate_scheme_with_order(field_value=field_value, ordered_list=party_list)
                if not field_value:
                    return

        field_name = xml_name if xml_name else field_name
        if parent:
            if self.result.get(parent):
                self.result[parent][field_name] = field_value
            else:
                self.result[parent] = {}
                if field_value:
                    self.result[parent][field_name] = field_value

        return field_value

    def has_any_other_buyer_id(self):
        for item in self.additional_fields_doc.other_buyer_ids:
            if strip(item.value):
                return True
        return False

    # TODO: Complete the implementation
    def validate_scheme_with_order(self, field_value: dict, ordered_list: list):
        rem_ordered_list = ordered_list
        res = {}

        for value in field_value:
            type_code = value.get('type_code')
            additional_id_value = (
                value.get('value').strip() or None if type(value.get('value')) is str else value.get('value')
            )

            if type_code not in ordered_list:
                return False
            elif type_code not in rem_ordered_list:
                return False
            elif additional_id_value is not None:
                res[type_code] = additional_id_value
                index = rem_ordered_list.index(type_code)
                rem_ordered_list = rem_ordered_list[index:]
        return res

    def get_customer_address_details(self, invoice_id):
        pass

    def get_customer_info(self, invoice_id):
        pass

    def compute_invoice_discount_amount(self):
        if self.sales_invoice_doc.doctype == 'Payment Entry':
            self.result['invoice']['allowance_total_amount'] = 0
            self.additional_fields_doc.fatoora_invoice_discount_amount = 0
            return
        discount_amount = abs(self.sales_invoice_doc.discount_amount)
        if self.sales_invoice_doc.apply_discount_on != 'Grand Total' or discount_amount == 0:
            self.additional_fields_doc.fatoora_invoice_discount_amount = discount_amount
            return

        applied_discount_percent = self.sales_invoice_doc.additional_discount_percentage
        total_without_vat = self.result['invoice']['line_extension_amount']
        tax_amount = abs(self.sales_invoice_doc.taxes[0].tax_amount)
        if applied_discount_percent == 0:
            applied_discount_percent = (discount_amount / (total_without_vat + tax_amount)) * 100
        applied_discount_amount = total_without_vat * (applied_discount_percent / 100)
        self.result['invoice']['allowance_total_amount'] = applied_discount_amount
        self.additional_fields_doc.fatoora_invoice_discount_amount = applied_discount_amount

    def get_business_settings_and_seller_details(self):
        # TODO: special validations handling
        has_branch_address = False
        if self.branch_doc:
            if self.branch_doc.custom_company_address:
                has_branch_address = True

            party_identification = self.get_list_value(
                field_name='custom_branch_ids',
                source_doc=self.branch_doc,
                xml_name='party_identifications',
                parent='seller_details',
            )
            if not party_identification:
                fthrow(
                    msg=ft(
                        'Commercial registration number is mandatory for branch $branch.',
                        branch=self.sales_invoice_doc.branch,
                    ),
                    title=ft('Mandatory CRN Error'),
                )
        else:
            self.get_list_value(
                field_name='other_ids',
                source_doc=self.business_settings_doc,
                xml_name='party_identifications',
                parent='seller_details',
            )

        self.get_text_value(
            field_name='custom_street' if has_branch_address else 'street',
            source_doc=self.branch_doc if has_branch_address else self.business_settings_doc,
            xml_name='street_name',
            parent='seller_details',
        )

        self.get_text_value(
            field_name='custom_additional_street' if has_branch_address else 'additional_street',
            source_doc=self.branch_doc if has_branch_address else self.business_settings_doc,
            xml_name='additional_street_name',
            parent='seller_details',
        )

        self.get_text_value(
            field_name='custom_building_number' if has_branch_address else 'building_number',
            source_doc=self.branch_doc if has_branch_address else self.business_settings_doc,
            xml_name='building_number',
            parent='seller_details',
        )

        self.get_text_value(
            field_name='additional_address_number',  # TODO: Fix missing field
            source_doc=self.business_settings_doc,
            xml_name='plot_identification',
            parent='seller_details',
        )

        self.get_text_value(
            field_name='custom_city' if has_branch_address else 'city',
            source_doc=self.branch_doc if has_branch_address else self.business_settings_doc,
            xml_name='city_name',
            parent='seller_details',
        )

        self.get_text_value(
            field_name='custom_postal_code' if has_branch_address else 'postal_code',
            source_doc=self.branch_doc if has_branch_address else self.business_settings_doc,
            xml_name='postal_zone',
            parent='seller_details',
        )

        self.get_text_value(
            field_name='province_state',  # TODO: Fix missing field
            source_doc=self.business_settings_doc,
            xml_name='CountrySubentity',
            parent='seller_details',
        )
        self.get_text_value(
            field_name='custom_district' if has_branch_address else 'district',
            source_doc=self.branch_doc if has_branch_address else self.business_settings_doc,
            xml_name='city_subdivision_name',
            parent='seller_details',
        )

        self.get_text_value(
            field_name='country_code',
            source_doc=self.business_settings_doc,
            xml_name='country_code',
            parent='seller_details',
        )

        self.get_text_value(
            field_name='vat_registration_number',
            source_doc=self.business_settings_doc,
            xml_name='company_id',
            parent='business_settings',
        )

        self.get_text_value(
            field_name='seller_name',
            source_doc=self.business_settings_doc,
            xml_name='registration_name',
            parent='business_settings',
        )

        # --------------------------- END Business Settings and Seller Details fields ------------------------------

    def get_buyer_details(self):
        # --------------------------- START Buyer Details fields ------------------------------
        self.get_list_value(
            field_name='other_buyer_ids',
            source_doc=self.additional_fields_doc,
            xml_name='party_identifications',
            parent='buyer_details',
        )

        self.get_text_value(
            field_name='buyer_street_name',
            source_doc=self.additional_fields_doc,
            xml_name='street_name',
            parent='buyer_details',
        )

        self.get_text_value(
            field_name='buyer_additional_street_name',
            source_doc=self.additional_fields_doc,
            xml_name='additional_street_name',
            parent='buyer_details',
        )

        self.get_text_value(
            field_name='buyer_building_number',
            source_doc=self.additional_fields_doc,
            xml_name='building_number',
            parent='buyer_details',
        )

        self.get_text_value(
            field_name='buyer_additional_number',
            source_doc=self.additional_fields_doc,
            xml_name='plot_identification',
            parent='buyer_details',
        )

        self.get_text_value(
            field_name='buyer_city', source_doc=self.additional_fields_doc, xml_name='city_name', parent='buyer_details'
        )

        self.get_text_value(
            field_name='buyer_postal_code',
            source_doc=self.additional_fields_doc,
            xml_name='postal_zone',
            parent='buyer_details',
        )

        self.get_text_value(
            field_name='buyer_province_state',
            source_doc=self.additional_fields_doc,
            xml_name='province',
            parent='buyer_details',
        )

        self.get_text_value(
            field_name='buyer_district',
            source_doc=self.additional_fields_doc,
            xml_name='city_subdivision_name',
            parent='buyer_details',
        )

        self.get_text_value(
            field_name='buyer_country_code',
            source_doc=self.additional_fields_doc,
            xml_name='country_code',
            parent='buyer_details',
        )

        self.get_text_value(
            field_name='buyer_vat_registration_number',
            source_doc=self.additional_fields_doc,
            xml_name='company_id',
            parent='buyer_details',
        )

        self.get_text_value(
            field_name='customer_name',
            source_doc=self.sales_invoice_doc,
            xml_name='registration_name',
            parent='buyer_details',
        )

        # --------------------------- END Buyer Details fields ------------------------------

    def append_to_item_lines(self, item_lines: list, is_tax_included: bool, sales_invoice_doc: SalesInvoice) -> None:
        """
        Appends items to item_lines list based on document type (Payment Entry or Sales Invoice).
        Handles tax-inclusive and tax-exclusive pricing calculations.
        """
        if sales_invoice_doc.doctype == 'Payment Entry':
            self._append_payment_entry_item(item_lines, sales_invoice_doc)
        else:
            self._append_sales_invoice_items(item_lines, is_tax_included, sales_invoice_doc)

    def _append_payment_entry_item(self, item_lines: list, doc: PaymentEntry) -> None:
        values = self._calculate_payment_entry_values(doc)
        """Handles payment entry specific item formatting."""
        item_data = {
            'idx': 1,
            'qty': 1.0,
            'uom': 'Unit',
            'item_code': 'Prepayment Invoice Item',
            'item_name': self.sales_invoice_doc.custom_prepayment_invoice_description or self.sales_invoice_doc.remarks,
            'net_amount': abs(values.net_amount),
            'amount_after_discount': abs(values.amount_after_discount),
            'amount': abs(values.amount),
            'base_net_rate': abs(self.sales_invoice_doc.received_amount),
            'base_net_amount': abs(self.sales_invoice_doc.received_amount),
            'line_extension_amount': abs(values.line_extension_amount),
            'base_amount': abs(self.sales_invoice_doc.received_amount),
            'rounding_amount': abs(values.rounding_amount),
            'rate': abs(self.sales_invoice_doc.received_amount),
            'discount_percentage': 0.0,
            'discount_amount': 0.0,
            'item_tax_template': None,
            'tax_percent': self.sales_invoice_doc.taxes[0].rate,
            'tax_amount': abs(values.tax_amount),
            'total_amount': abs(self.sales_invoice_doc.received_amount_after_tax),
        }

        item_lines.append(frappe._dict(item_data))

    def _calculate_payment_entry_values(self, doc: PaymentEntry) -> dict:
        values = frappe._dict()
        if not doc.taxes:
            fthrow(
                msg=ft(
                    'Payment Entry $name does not have any taxes. Please add taxes to the Payment Entry.', name=doc.name
                )
            )
        charge_type = doc.taxes[0].charge_type
        tax_percent = abs(doc.taxes[0].rate) / 100
        if charge_type == 'Actual':
            values.amount_after_discount = doc.paid_amount - doc.total_taxes_and_charges
            values.line_extension_amount = doc.paid_amount - doc.total_taxes_and_charges
            values.amount = abs(self.sales_invoice_doc.received_amount_after_tax)
            values.rounding_amount = doc.paid_amount
            values.net_amount = abs(self.sales_invoice_doc.received_amount_after_tax)
            values.tax_amount = abs(doc.total_taxes_and_charges)
        else:
            sales_order_found = False
            for row in doc.references:
                if row.reference_doctype == 'Sales Order':
                    sales_order_found = True
                    break
            if not sales_order_found:
                fthrow(
                    msg=ft(
                        'You cannot set Charge Type to anything other than Actual for Prepayment Invoice. If there is no Sales Order; please set Charge Type to Actual.'
                    )
                )
            tax_amount = abs(self.sales_invoice_doc.received_amount) - (
                abs(self.sales_invoice_doc.received_amount) / (1 + tax_percent)
            )
            values.amount_after_discount = abs(self.sales_invoice_doc.received_amount)
            values.line_extension_amount = abs(self.sales_invoice_doc.received_amount)
            values.rounding_amount = abs(self.sales_invoice_doc.received_amount)
            values.amount = abs(self.sales_invoice_doc.received_amount) - abs(tax_amount)
            values.net_amount = abs(self.sales_invoice_doc.received_amount) - abs(tax_amount)
            values.tax_amount = abs(tax_amount)

        return values

    def _append_sales_invoice_items(self, item_lines: list, is_tax_included: bool, doc: SalesInvoice) -> None:
        """Processes regular sales invoice items with proper tax and discount calculations."""
        for item in doc.items:
            has_discount = isinstance(item.discount_amount, float) and item.discount_amount > 0

            tax_percent = abs(item.tax_rate or 0.0)
            tax_amount_with_qty = abs(item.tax_amount or 0.0)
            discount_with_qty = abs(item.discount_amount * item.qty) if has_discount else 0.0
            amount_with_qty = abs(
                flt(abs(item.amount) / (1 + (tax_percent / 100)), 2) if is_tax_included else item.amount
            )
            net_amount_with_qty = abs(item.net_amount)
            rate_without_qty = abs(item.rate)
            item_data = {
                'idx': item.idx,
                'qty': abs(item.qty),
                'uom': item.uom,
                'item_code': item.item_code,
                'item_name': item.item_name,
                'net_amount': net_amount_with_qty,
                'rate': rate_without_qty,
                'discount_percentage': abs(item.discount_percentage) if has_discount else 0.0,
                'tax_percent': tax_percent,
                'amount': amount_with_qty,
                'rounding_amount': tax_amount_with_qty + amount_with_qty,
                'base_amount': amount_with_qty + discount_with_qty,
                'discount_amount': discount_with_qty if has_discount else 0.0,
                'tax_amount': tax_amount_with_qty,
                'item_tax_template': item.item_tax_template,
                'allowance_charge_reason': None,
                'allowance_charge_reason_code': None,
            }
            if item_data['discount_amount']:
                zatca_discount_reason = get_zatca_discount_reason_by_name(
                    item.get('custom_zatca_discount_reason') or 'Discount'
                )
                item_data['allowance_charge_reason'] = zatca_discount_reason.name
                item_data['allowance_charge_reason_code'] = zatca_discount_reason.code
            item_lines.append(frappe._dict(item_data))

    def get_e_invoice_details(self, invoice_type: str):
        is_standard = invoice_type == 'Standard'

        # --------------------------- START Invoice fields ------------------------------
        # --------------------------- START Invoice Basic info ------------------------------
        self.get_text_value(field_name='name', source_doc=self.sales_invoice_doc, xml_name='id', parent='invoice')

        self.get_text_value(field_name='uuid', source_doc=self.additional_fields_doc, xml_name='uuid', parent='invoice')

        self.get_date_value(
            field_name='posting_date', source_doc=self.sales_invoice_doc, xml_name='issue_date', parent='invoice'
        )

        self.get_time_value(
            field_name='posting_time', source_doc=self.sales_invoice_doc, xml_name='issue_time', parent='invoice'
        )

        if is_standard:
            # TODO: Review this with business and finalize
            self.get_date_value(
                field_name='due_date', source_doc=self.sales_invoice_doc, xml_name='delivery_date', parent='invoice'
            )

        self.get_text_value(
            field_name='invoice_type_code',
            source_doc=self.additional_fields_doc,
            xml_name='invoice_type_code',
            parent='invoice',
        )

        self.get_text_value(
            field_name='invoice_type_transaction',
            source_doc=self.additional_fields_doc,
            xml_name='invoice_type_transaction',
            parent='invoice',
        )

        self.get_text_value(
            field_name='currency', source_doc=self.sales_invoice_doc, xml_name='currency_code', parent='invoice'
        )
        # Default "SAR"
        self.get_text_value(
            field_name='tax_currency', source_doc=self.additional_fields_doc, xml_name='tax_currency', parent='invoice'
        )

        self.get_bool_value(
            field_name='is_return', source_doc=self.sales_invoice_doc, xml_name='is_return', parent='invoice'
        )

        self.get_bool_value(
            field_name='is_debit_note', source_doc=self.sales_invoice_doc, xml_name='is_debit_note', parent='invoice'
        )

        self.get_int_value(
            field_name='invoice_counter',
            source_doc=self.additional_fields_doc,
            xml_name='invoice_counter_value',
            parent='invoice',
        )

        self.get_text_value(
            field_name='previous_invoice_hash', source_doc=self.additional_fields_doc, xml_name='pih', parent='invoice'
        )

        if self.sales_invoice_doc.get('is_debit_note') or self.sales_invoice_doc.get('is_return'):
            billing_references = []
            if self.sales_invoice_doc.return_against:
                billing_references.append(self.sales_invoice_doc.return_against)

            additional_references = cast(
                List[ZATCAReturnAgainstReference] | None,
                self.sales_invoice_doc.get('custom_return_against_additional_references'),
            )
            if additional_references:
                billing_references.extend([ref.sales_invoice for ref in additional_references])

            self.result['invoice']['billing_references'] = billing_references

        # FIXME: Contracting (contract ID)
        if self.sales_invoice_doc.get('contract_id'):
            self.get_text_value(
                field_name='contract_id',
                source_doc=self.additional_fields_doc,
                xml_name='contract_id',
                parent='invoice',
            )

        self.get_float_value(field_name='total', source_doc=self.sales_invoice_doc, xml_name='total', parent='invoice')

        self.get_float_value(
            field_name='net_total', source_doc=self.sales_invoice_doc, xml_name='net_total', parent='invoice'
        )

        self.get_float_value(
            field_name='total_taxes_and_charges',
            source_doc=self.sales_invoice_doc,
            xml_name='total_taxes_and_charges',
            parent='invoice',
        )

        self.get_float_value(
            field_name='base_total_taxes_and_charges',
            source_doc=self.sales_invoice_doc,
            xml_name='base_total_taxes_and_charges',
            parent='invoice',
        )
        # TODO: Tax Account Currency
        self.get_float_value(
            field_name='grand_total', source_doc=self.sales_invoice_doc, xml_name='grand_total', parent='invoice'
        )
        self.get_float_value(
            field_name='total_advance', source_doc=self.sales_invoice_doc, xml_name='prepaid_amount', parent='invoice'
        )

        self.get_float_value(
            field_name='outstanding_amount',
            source_doc=self.sales_invoice_doc,
            xml_name='outstanding_amount',
            parent='invoice',
        )
        self.get_float_value(
            field_name='net_amount',
            source_doc=self.sales_invoice_doc,
            xml_name='VAT_category_taxable_amount',
            parent='invoice',
        )

        self.get_text_value(
            field_name='po_no', source_doc=self.sales_invoice_doc, xml_name='purchase_order_reference', parent='invoice'
        )

        # --------------------------- END Invoice Basic info ------------------------------
        # --------------------------- Start Getting Invoice's item lines ------------------------------
        item_lines = []
        is_tax_included = self.sales_invoice_doc.taxes[0].get(
            get_right_fieldname('included_in_print_rate', self.sales_invoice_doc.doctype)
        )
        self.append_to_item_lines(item_lines, is_tax_included, self.sales_invoice_doc)
        tax_categories = create_tax_categories(self.sales_invoice_doc, item_lines, is_tax_included)
        tax_total = create_tax_total(tax_categories)
        self.result['invoice']['tax_total'] = tax_total
        allowance_charge = create_allowance_charge(self.sales_invoice_doc, tax_total)
        self.result['invoice']['allowance_charge'] = allowance_charge
        # Calculate allowance_total_amount as sum of all allowance charges to ensure BR-CO-11 compliance
        self.result['invoice']['allowance_total_amount'] = sum(ac.get('amount', 0) for ac in allowance_charge)

        # Add invoice total taxes and charges percentage field
        self.result['invoice']['total_taxes_and_charges_percent'] = sum(
            it.rate for it in self.sales_invoice_doc.get('taxes', [])
        )
        if self.sales_invoice_doc.doctype == 'Payment Entry':
            charge_type = self.sales_invoice_doc.taxes[0].charge_type
            tax_percent = abs(self.sales_invoice_doc.taxes[0].rate) / 100
            # Recalculated prepayment on Sales Order to include tax in the paid amount.
            if charge_type != 'Actual':
                self.result['invoice']['base_total_taxes_and_charges'] = abs(
                    self.sales_invoice_doc.base_total_taxes_and_charges
                ) / (1 + tax_percent)
                self.result['invoice']['total_taxes_and_charges'] = abs(
                    self.sales_invoice_doc.total_taxes_and_charges
                ) / (1 + tax_percent)

        self.result['invoice']['item_lines'] = item_lines
        self.result['invoice']['line_extension_amount'] = sum(it['amount'] for it in item_lines)
        # Note: allowance_total_amount is now set from allowance_charge list above to ensure BR-CO-11 compliance
        # self.compute_invoice_discount_amount()
        self.result['invoice']['net_total'] = (
            self.result['invoice']['line_extension_amount'] - self.result['invoice']['allowance_total_amount']
        )
        if self.sales_invoice_doc.doctype == 'Payment Entry':
            if self.sales_invoice_doc.taxes[0].included_in_paid_amount:
                self.result['invoice']['net_total'] = (
                    self.sales_invoice_doc.paid_amount - self.sales_invoice_doc.total_taxes_and_charges
                )
        self.result['invoice']['grand_total'] = (
            self.result['invoice']['net_total'] + self.result['invoice']['total_taxes_and_charges']
        )
        rounding_adjustment = 0
        if self.sales_invoice_doc.doctype != 'Payment Entry':
            rounding_adjustment = self.sales_invoice_doc.rounding_adjustment

        self.result['invoice']['payable_amount'] = self.result['invoice']['grand_total'] + rounding_adjustment
        self.result['invoice']['rounding_adjustment'] = rounding_adjustment

        if self.sales_invoice_doc.doctype == 'Payment Entry':
            return
        if self.sales_invoice_doc.doctype == 'POS Invoice':
            return
        if self.sales_invoice_doc.doctype == 'Sales Invoice' and not self.sales_invoice_doc.advances:
            return
        self.result['prepayment_invoice'] = prepayment_invoice_factory_create(self.sales_invoice_doc)
        update_result(self.result, self.sales_invoice_doc)
        # --------------------------- END Getting Invoice's item lines ------------------------------
