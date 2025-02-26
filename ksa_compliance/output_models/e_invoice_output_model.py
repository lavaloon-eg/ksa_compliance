from __future__ import annotations

from typing import cast, Optional, List

import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.setup.doctype.branch.branch import Branch
from frappe.model.document import Document
from frappe.utils import get_date_str, get_time, strip, flt
from ksa_compliance.invoice import InvoiceType
from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields import sales_invoice_additional_fields
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings
from ksa_compliance.ksa_compliance.doctype.zatca_return_against_reference.zatca_return_against_reference import (
    ZATCAReturnAgainstReference,
)
from ksa_compliance.standard_doctypes.tax_category import map_tax_category
from ksa_compliance.throw import fthrow
from ksa_compliance.translation import ft


def append_tax_details_into_item_lines(item_lines: list, is_tax_included: bool) -> list:
    for item in item_lines:
        tax_percent = item['tax_percent']
        tax_amount = item['tax_amount']

        """
            In case of tax included we should get the item amount exclusive of vat from the current 'item amount', 
            and Since ERPNext discount on invoice affects the item tax amount we cannot simply subtract the item tax amount
            from the item amount but we need to get the tax amount without being affected by applied discount, so we 
            use this calculation to get the actual item amount exclusive of vat: "item_amount / 1 + tax_percent"
        """
        item['amount'] = flt(abs(item['amount']) / (1 + (tax_percent / 100)), 2) if is_tax_included else item['amount']
        item['discount_amount'] = item['discount_amount'] * item['qty']
        item['base_amount'] = item['amount'] + item['discount_amount']
        item['tax_percent'] = tax_percent
        item['tax_amount'] = tax_amount
        item['total_amount'] = tax_amount + abs(item['amount'])

    return item_lines


def append_tax_categories_to_item(item_lines: list, taxes_and_charges: str | None) -> list:
    """
    Append tax category of each item based on item tax template or sales taxes and charges template in sales invoice.
    Returns unique Tax Categories with sum of item taxable amount and item tax amount per tax category.
    """
    if taxes_and_charges:
        tax_category_id = frappe.get_value('Sales Taxes and Charges Template', taxes_and_charges, 'tax_category')
    else:
        tax_category_id = None
    unique_tax_categories = {}
    for item in item_lines:
        if item['item_tax_template']:
            item_tax_category = map_tax_category(item_tax_template_id=item['item_tax_template'])
        else:
            if tax_category_id:
                item_tax_category = map_tax_category(tax_category_id=tax_category_id)
            else:
                item_tax_category = None
                frappe.throw(
                    "Please Include Sales Taxes and Charges Template on invoice\n"
                    f"Or include Item Tax Template on {item['item_name']}"
                )

        item['tax_category_code'] = item_tax_category.tax_category_code
        item_tax_category_details = {
            'tax_category_code': item['tax_category_code'],
            'tax_amount': item['tax_amount'],
            'tax_percent': item['tax_percent'],
            'taxable_amount': item['net_amount'],
            'total_discount': item['amount'] - item['net_amount'],
        }
        if item_tax_category.reason_code:
            item['tax_exemption_reason_code'] = item_tax_category.reason_code
            item_tax_category_details['tax_exemption_reason_code'] = item_tax_category.reason_code
        if item_tax_category.arabic_reason:
            item['tax_exemption_reason'] = item_tax_category.arabic_reason
            item_tax_category_details['tax_exemption_reason'] = item_tax_category.arabic_reason

        key = item_tax_category.tax_category_code + str(item_tax_category.reason_code) + str(item['tax_percent'])
        if key in unique_tax_categories:
            unique_tax_categories[key]['tax_amount'] += item_tax_category_details['tax_amount']
            unique_tax_categories[key]['taxable_amount'] += item_tax_category_details['taxable_amount']
            unique_tax_categories[key]['total_discount'] += item_tax_category_details['total_discount']
        else:
            unique_tax_categories[key] = item_tax_category_details

    return list(unique_tax_categories.values())


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
        }

        self.sales_invoice_doc = cast(
            SalesInvoice,
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
        self.get_buyer_details(invoice_type=invoice_type)

        # Get E-Invoice Fields
        self.get_e_invoice_details(invoice_type)

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

        self.get_text_value(
            field_name='reason_for_allowance',
            source_doc=self.additional_fields_doc,
            xml_name='allowance_charge_reason',
            parent='invoice',
        )

        self.get_text_value(
            field_name='code_for_allowance_reason',
            source_doc=self.additional_fields_doc,
            xml_name='allowance_charge_reason_code',
            parent='invoice',
        )

        # Allowance on invoice should be only the document level allowance without items allowances.
        self.get_float_value(
            field_name='discount_amount',
            source_doc=self.sales_invoice_doc,
            xml_name='allowance_total_amount',
            parent='invoice',
        )
        self.compute_invoice_discount_amount()

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
            xml_name='allowance_charge_reason',
            parent='invoice',
        )

        self.get_text_value(
            field_name='reason_for_charge_code',
            source_doc=self.additional_fields_doc,
            xml_name='allowance_charge_reason_code',
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
        field_value = source_doc.get(field_name).strip() if source_doc.get(field_name) else None

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
        field_value = cast(any, source_doc.get(field_name))

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
        field_value = source_doc.get(field_name, None)
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

    def get_buyer_details(self, invoice_type):
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

        if self.sales_invoice_doc.is_rounded_total_disabled():
            self.result['invoice']['payable_amount'] = abs(self.sales_invoice_doc.grand_total)
            self.result['invoice']['rounding_adjustment'] = 0.0
        else:
            # Tax inclusive amount + rounding adjustment = payable amount
            # However, ZATCA doesn't accept negative values for tax inclusive amount or payable amount, so we put their
            # absolute values.
            # For return invoices, we can have a positive rounding adjustment (if it were negative in the original invoice)
            # The calculation works out if tax inclusive amount and payable amount are negative, but it doesn't work with
            # the abs values we send to ZATCA.
            # For example:
            # Original invoice: 100.25 + (-0.25) = 100
            # Return invoice (ERPNext): -100.25 + 0.25 = -100
            # Return invoice (XML): abs(-100.25) + 0.25 = 100.25
            # So the calculation would be wrong if we just used the value of rounding adjustment. We need to recalculate
            # it or adjust its sign to produce the right result in the return case
            payable_amount = abs(self.sales_invoice_doc.rounded_total)
            tax_inclusive_amount = abs(self.sales_invoice_doc.grand_total)
            self.result['invoice']['payable_amount'] = payable_amount
            if self.sales_invoice_doc.is_return:
                self.result['invoice']['rounding_adjustment'] = payable_amount - tax_inclusive_amount
            else:
                self.result['invoice']['rounding_adjustment'] = self.sales_invoice_doc.rounding_adjustment

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
        for item in self.sales_invoice_doc.items:
            # Negative discount is used to adjust price up, but it's not really a discount in that case
            has_discount = isinstance(item.discount_amount, float) and item.discount_amount > 0

            # noinspection PyUnresolvedReferences
            tax_percent = abs(item.tax_rate or 0.0)
            # noinspection PyUnresolvedReferences
            tax_amount = abs(item.tax_amount or 0.0)

            # We use absolute values for int/float values because we want positive values in the XML in the return invoice
            # case
            item_lines.append(
                {
                    'idx': item.idx,
                    'qty': abs(item.qty),
                    'uom': item.uom,
                    'item_code': item.item_code,
                    'item_name': item.item_name,
                    'net_amount': abs(item.net_amount),
                    'amount': abs(item.amount),
                    'rate': abs(item.rate),
                    'discount_percentage': abs(item.discount_percentage) if has_discount else 0.0,
                    'discount_amount': abs(item.discount_amount) if has_discount else 0.0,
                    'item_tax_template': item.item_tax_template,
                    'tax_percent': tax_percent,
                    'tax_amount': tax_amount,
                }
            )

        # Add tax amount and tax percent on each item line
        is_tax_included = bool(self.sales_invoice_doc.taxes[0].included_in_print_rate)
        item_lines = append_tax_details_into_item_lines(item_lines=item_lines, is_tax_included=is_tax_included)
        unique_tax_categories = append_tax_categories_to_item(item_lines, self.sales_invoice_doc.taxes_and_charges)
        # Append unique Tax categories to invoice
        self.result['invoice']['tax_categories'] = unique_tax_categories

        # Add invoice total taxes and charges percentage field
        self.result['invoice']['total_taxes_and_charges_percent'] = sum(
            it.rate for it in self.sales_invoice_doc.get('taxes', [])
        )
        self.result['invoice']['item_lines'] = item_lines
        self.result['invoice']['line_extension_amount'] = sum(it['amount'] for it in item_lines)
        # --------------------------- END Getting Invoice's item lines ------------------------------
