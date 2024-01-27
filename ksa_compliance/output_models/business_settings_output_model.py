import frappe
from frappe.utils import get_date_str, get_time_str


def get_sales_invoice_by_id(invoice_id: str):
    return frappe.get_doc("Sales Invoice", invoice_id).as_dict()


def get_business_settings_doc(company_id: str):
    company_doc = frappe.get_doc("Company", company_id)
    business_settings_id = company_id + '-' + company_doc.get("country") + '-' + company_doc.get("default_currency")
    return frappe.get_doc("ZATCA Business Settings", business_settings_id).as_dict()


class Einvoice:
    # TODO: if batch doc = none validate business settings else pass

    def __init__(self, sales_invoice_additional_fields_doc, invoice_type: str = "Simplified", batch_doc=None):

        self.additional_fields_doc = sales_invoice_additional_fields_doc.as_dict()
        self.batch_doc = batch_doc
        self.result = {}
        self.error_dic = {}

        self.sales_invoice_doc = get_sales_invoice_by_id(sales_invoice_additional_fields_doc.get("sales_invoice"))
        self.business_settings_doc = get_business_settings_doc(self.sales_invoice_doc.get("company"))

        # Get Business Settings and Seller Fields
        self.get_business_settings_and_seller_details()

        # Get Buyer Fields
        self.get_buyer_details(invoice_type=invoice_type)

        # Get E-Invoice Fields
        self.get_e_invoice_details()  # TODO: Implement the rest of fields

        # TODO: Delivery (Supply start and end dates)
        # TODO: Allowance Charge (Discount)
        # FIXME: IF invoice is pre-paid
        self.get_text_value(field_name="payment_means_type_code",
                            source_doc=self.additional_fields_doc,
                            required=False,
                            xml_name="PaymentMeansCode",
                            rules=["BR-KSA-16", "BR-49", "BR-CL-16", "BT-81", "BG-16"],
                            parent="invoice")

        if self.sales_invoice_doc.get("is_debit_note") or self.sales_invoice_doc.get("is_return"):
            # TODO: handle conditional view and mandatory in sales invoice doctype
            self.get_text_value(field_name="custom_return_reason",
                                source_doc=self.sales_invoice_doc,
                                required=True,
                                xml_name="PaymentMeansCode",
                                min_length=1,
                                max_length=1000,
                                rules=["BR-KSA-17", "BR-KSA-F-06", "KSA-10"],
                                parent="invoice")

        # TODO: payment mode return Payment by credit?
        # if self.sales_invoice_doc.get("mode_of_payment") == "Credit":

        # TODO: field from 49 to 58

        self.get_text_value(field_name="reason_for_allowance",
                            source_doc=self.additional_fields_doc,
                            required=False,
                            xml_name="allowance_charge_reason",
                            min_length=0,
                            max_length=1000,
                            rules=["BR-KSA-F-06", "BT-97", "BG-20"],
                            parent="invoice")

        self.get_text_value(field_name="code_for_allowance_reason",
                            source_doc=self.additional_fields_doc,
                            required=False,
                            xml_name="allowance_charge_reason_code",
                            min_length=0,
                            max_length=1000,
                            rules=["BR-KSA-F-06", "BT-97", "BG-20"],
                            parent="invoice")

        #     TAX ID Scheme is Hardcoded
        self.get_text_value(field_name="code_for_allowance_reason",
                            source_doc=self.additional_fields_doc,
                            required=False,
                            xml_name="allowance_charge_reason_code",
                            min_length=0,
                            max_length=1000,
                            rules=["BR-KSA-F-06", "BT-97", "BG-20"],
                            parent="invoice")
        #     TODO: validate Document level charge indicator is Hardcoded, conditional fields from 63 to 72

        # TODO: Add Conditional Case
        self.get_float_value(field_name='charge_percentage',
                             source_doc=self.additional_fields_doc,
                             required=False,
                             xml_name="multiplier_factor_numeric",
                             min_value=0,
                             max_value=100,
                             rules=["BR-KSA-EN16931-03", "BR-KSA-EN16931-04", "BR-KSA-EN16931-05", "BT-101", "BG-21"],
                             parent="invoice")

        # TODO: Add Conditional Case
        self.get_float_value(field_name='charge_amount',
                             source_doc=self.additional_fields_doc,
                             required=False,
                             xml_name="amount",
                             rules=["BR-KSA-F-04", "BR-KSA-EN16931-03", "BR-36", "BR-DEC-05", "BT-99", "BG-21"],
                             parent="invoice")

    # --------------------------- START helper functions ------------------------------
    def get_text_value(self, field_name: str, source_doc: dict, required: bool, xml_name: str = None,
                       min_length: int = 0, max_length: int = 5000, rules: list = None, parent: str = None):
        if required and field_name not in source_doc:
            self.error_dic[field_name] = f"Missing field"
            return

        field_value = source_doc.get(field_name).strip() if source_doc.get(field_name) else None
        if required and field_value is None:
            self.error_dic[field_name] = f"Missing field value: {field_name}."
            return
        if field_value is None:
            return

        if not min_length <= len(field_value) <= max_length:
            self.error_dic[field_name] = f'Invalid {field_name} field size value {len(field_value)}'
            return

        field_name = xml_name if xml_name else field_name
        if parent:
            if self.result.get(parent):
                self.result[parent][field_name] = field_value
            else:
                self.result[parent] = {}
                self.result[parent][field_name] = field_value

        return field_value

    def get_int_value(self, field_name: str, source_doc: dict, required: bool, min_value: int,
                      max_value: int, xml_name: str = None, rules: list = None, parent: str = None):
        if required and field_name not in source_doc:
            self.error_dic[field_name] = f"Missing field"
            return

        field_value = source_doc.get(field_name, None)
        if required and field_value is None:
            self.error_dic[field_name] = f"Missing field value: {field_name}."
            return

        if field_value is None:
            return

        if not min_value <= field_value <= max_value:
            self.error_dic[field_name] = f'field value must be between {min_value} and {max_value}'
            return

        field_name = xml_name if xml_name else field_name
        if parent:
            if self.result.get(parent):
                self.result[parent][field_name] = field_value
            else:
                self.result[parent] = {}
                self.result[parent][field_name] = field_value
        return field_value

    def get_float_value(self, field_name: str, source_doc: dict, required: bool, min_value: int = 0,
                        max_value: int = 99999999999999, xml_name: str = None, rules: list = None, parent: str = None):
        if required and field_name not in source_doc:
            self.error_dic[field_name] = f"Missing field"
            return

        field_value = source_doc.get(field_name, None)
        if required and field_value is None:
            self.error_dic[field_name] = f"Missing field value: {field_name}."
            return
        if field_value is None:
            return

        # Try to parse
        field_value = float(field_value) if type(field_value) is int else field_value
        if not min_value <= field_value <= max_value:
            self.error_dic[field_name] = f'field value must be between {min_value} and {max_value}'
            return

        field_name = xml_name if xml_name else field_name
        if parent:
            if self.result.get(parent):
                self.result[parent][field_name] = field_value
            else:
                self.result[parent] = {}
                self.result[parent][field_name] = field_value
        return field_value

    def get_date_value(self, field_name, source_doc, required, xml_name, rules, parent):
        if required and field_name not in source_doc:
            self.error_dic[field_name] = f"Missing field"
            return

        field_value = source_doc.get(field_name, None)
        if required and field_value is None:
            self.error_dic[field_name] = f"Missing field value: {field_name}."
            return
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

    def get_time_value(self, field_name, source_doc, required, xml_name, rules, parent):
        if required and field_name not in source_doc:
            self.error_dic[field_name] = f"Missing field"
            return

        field_value = source_doc.get(field_name, None)
        if required and field_value is None:
            self.error_dic[field_name] = f"Missing field value: {field_name}."
            return
        if field_value is None:
            return

        # Try to parse
        field_value = get_time_str(field_value)

        field_name = xml_name if xml_name else field_name
        if parent:
            if self.result.get(parent):
                self.result[parent][field_name] = field_value
            else:
                self.result[parent] = {}
                self.result[parent][field_name] = field_value
        return field_value

    def get_dict_value(self, field_name: str, source_doc: dict, required: bool, xml_name: str = None,
                       rules: list = None, parent: str = None):
        if required and field_name not in source_doc:
            self.error_dic[field_name] = f"Missing field"
            return

        field_value = source_doc.get(field_name)
        if required and (not field_value or {}):
            self.error_dic[field_name] = f"Missing field value: {field_name}."
            return
        if field_value is None or {}:
            return

        if xml_name == 'party_identifications':
            party_list = ["CRN", "MOM", "MLS", "700", "SAG", "OTH"]
            if field_value:
                valid = self.validate_scheme_with_order(field_value=field_value, ordered_list=party_list)
                if not valid:
                    self.error_dic[field_name] = f"Wrong ordered for field: {field_name}."
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

    def get_list_value(self, field_name: str, source_doc: dict, required: bool, xml_name: str = None,
                       rules: list = None, parent: str = None):
        if required and field_name not in source_doc:
            self.error_dic[field_name] = f"Missing field"
            return

        field_value = source_doc.get(field_name, None)
        if required and (field_value is None or []):
            self.error_dic[field_name] = f"Missing field value: {field_name}."
            return
        if field_value is None or []:
            return

        field_name = xml_name if xml_name else field_name
        if parent:
            if self.result.get(parent):
                self.result[parent][field_name] = field_value
            else:
                self.result[parent] = {}
                self.result[parent][field_name] = field_value
        return field_value

    # TODO: Complete the implementation
    def validate_scheme_with_order(self, field_value: dict, ordered_list: list):
        rem_ordered_list = ordered_list

        for scheme_id, scheme_value in field_value.items():
            if scheme_id not in ordered_list:
                self.error_dic['party_identification'] = f"Invalid scheme ID: {scheme_id} for Seller Additional IDs"
                return False
            elif scheme_id not in rem_ordered_list:
                self.error_dic['party_identification'] = (
                    f"Invalid scheme ID Order: "
                    f"for {field_value} in Additional IDs")
                return False
            else:
                index = rem_ordered_list.index(scheme_id)
                rem_ordered_list = rem_ordered_list[index:]
        return True

    def get_customer_address_details(self, invoice_id):
        pass

    def get_customer_info(self, invoice_id):
        pass

    def get_business_settings_and_seller_details(self):
        # TODO: special validations handling
        self.get_dict_value(field_name="other_ids",
                            source_doc=self.business_settings_doc,
                            required=True,
                            xml_name="party_identifications",
                            rules=["BR-KSA-08", "BT-29", "BT-29-1", "BG-5"],
                            parent="seller_details")

        self.get_text_value(field_name="street",
                            source_doc=self.business_settings_doc,
                            required=True,
                            xml_name="street_name",
                            min_length=1,
                            max_length=127,
                            rules=["BR-KSA-09", "BR-KSA-F-06", "BR-08", "BT-35", "BG-5"],
                            parent="seller_details")

        self.get_text_value(field_name="additional_street",
                            source_doc=self.business_settings_doc,
                            required=False,
                            xml_name="additional_street_name",
                            min_length=0,
                            max_length=127,
                            rules=["BR-KSA-F-06", "BR-08", "BT-36", "BG-5"],
                            parent="seller_details")

        self.get_text_value(field_name="building_number",
                            source_doc=self.business_settings_doc,
                            required=True,
                            xml_name="building_number",
                            rules=["BR-KSA-09", "BR-KSA-37", "BR-08", "KSA-17", "BG-5"],
                            parent="seller_details")

        self.get_text_value(field_name="additional_address_number",  # TODO: Fix missing field
                            source_doc=self.business_settings_doc,
                            required=False,
                            xml_name="plot_identification",
                            rules=["BR-08", "KSA-23", "BG-5"],
                            parent="seller_details")

        self.get_text_value(field_name="city",
                            source_doc=self.business_settings_doc,
                            required=True,
                            xml_name="city_name",
                            rules=["BR-KSA-09", "BR-KSA-F-06", "BR-08", "BT-37", "BG-5"],
                            parent="seller_details")

        self.get_text_value(field_name="postal_code",
                            source_doc=self.business_settings_doc,
                            required=True,
                            xml_name="postal_zone",
                            rules=["BR-KSA-09", "BR-KSA-66", "BR-08", "BT-38", "BG-5"],
                            parent="seller_details")

        self.get_text_value(field_name="province_state",  # TODO: Fix missing field
                            source_doc=self.business_settings_doc,
                            required=False,
                            xml_name="CountrySubentity",
                            min_length=0,
                            max_length=127,
                            rules=["BR-KSA-F-06", "BR-08", "BT-39", "BG-5"],
                            parent="seller_details")

        self.get_text_value(field_name="district",
                            source_doc=self.business_settings_doc,
                            required=True,
                            xml_name="city_subdivision_name",
                            min_length=1,
                            max_length=127,
                            rules=["BR-KSA-09", "BR-KSA-F-06", "BR-08", "KSA-3", "BG-5"],
                            parent="seller_details")

        self.get_text_value(field_name="country",
                            source_doc=self.business_settings_doc,
                            required=True,
                            xml_name="country",
                            rules=["BG-5", "BT-40", "BR-08", "BR-09", "BR-CL-14"],
                            parent="seller_details")

        self.get_text_value(field_name="vat_registration_number",
                            source_doc=self.business_settings_doc,
                            required=True,
                            xml_name="company_id",
                            rules=["BR-KSA-39", "BR-KSA-40", "BT-31", "BG-5"],
                            parent="business_settings")

        self.get_text_value(field_name="seller_name",
                            source_doc=self.business_settings_doc,
                            required=True,
                            xml_name="registration_name",
                            min_length=1,
                            max_length=1000,
                            rules=["BR-KSA-F-06", "BR-06", "BT-27", "BG-5"],
                            parent="business_settings")

        # --------------------------- END Business Settings and Seller Details fields ------------------------------

    def get_buyer_details(self, invoice_type):
        # --------------------------- START Buyer Details fields ------------------------------
        self.get_dict_value(field_name="other_buyer_identification",  # TODO: Fix Add to doctype customer and additional
                            source_doc=self.sales_invoice_doc,
                            required=True,
                            xml_name="PartyIdentification",
                            rules=["BR-KSA-08", "BT-29", "BT-29-1", "BG-5"],
                            parent="buyer_details")

        if invoice_type == "Standard":
            self.get_text_value(field_name="buyer_street_name",
                                source_doc=self.additional_fields_doc,
                                required=True,
                                xml_name="street_name",
                                min_length=1,
                                max_length=127,
                                rules=["BR-KSA-10", "BR-KSA-63", "BR-KSA-F-06", "BR-10", "BT-50", "BG-8"],
                                parent="buyer_details")
        elif invoice_type == "Simplified":
            self.get_text_value(field_name="buyer_street_name",
                                source_doc=self.additional_fields_doc,
                                required=False,
                                xml_name="street_name",
                                min_length=0,
                                max_length=127,
                                rules=["BR-KSA-10", "BR-KSA-63", "BR-KSA-F-06", "BR-10", "BT-50", "BG-8"],
                                parent="buyer_details")

        self.get_text_value(field_name="buyer_additional_street_name",
                            source_doc=self.additional_fields_doc,
                            required=False,
                            xml_name="additional_street_name",
                            min_length=0,
                            max_length=127,
                            rules=["BR-KSA-F-06", "BT-51", "BG-8"],
                            parent="buyer_details")

        self.get_text_value(field_name="buyer_building_number",
                            source_doc=self.additional_fields_doc,
                            required=False,
                            xml_name="building_number",
                            rules=["KSA-18", "BG-8"],
                            parent="buyer_details")

        self.get_text_value(field_name="buyer_additional_number",
                            # TODO: add additional number field for address if needed
                            source_doc=self.additional_fields_doc,
                            required=False,
                            xml_name="plot_identification",
                            rules=["KSA-19", "BG-8"],
                            parent="buyer_details")

        if invoice_type == "Standard":
            self.get_text_value(field_name="buyer_city",
                                source_doc=self.additional_fields_doc,
                                required=True,
                                xml_name="city_name",
                                min_length=1,
                                max_length=127,
                                rules=["BR-KSA-10", "BR-KSA-63", "BR-KSA-F-06", "BR-10", "BT-52", "BG-8"],
                                parent="buyer_details")
        elif invoice_type == "Simplified":
            self.get_text_value(field_name="buyer_city",
                                source_doc=self.additional_fields_doc,
                                required=False,
                                xml_name="city_name",
                                min_length=0,
                                max_length=127,
                                rules=["BR-KSA-10", "BR-KSA-63", "BR-KSA-F-06", "BR-10", "BT-52", "BG-8"],
                                parent="buyer_details")

        if invoice_type == "Standard":
            self.get_text_value(field_name="postal_code",
                                source_doc=self.business_settings_doc,
                                required=True,
                                xml_name="postal_zone",
                                rules=["BR-KSA-09", "BR-KSA-66", "BR-08", "BT-38", "BG-5"],
                                parent="buyer_details")
        elif invoice_type == "Simplified":
            self.get_text_value(field_name="buyer_postal_code",
                                source_doc=self.additional_fields_doc,
                                required=False,
                                xml_name="postal_zone",
                                rules=["BR-10", "BT-53", "BG-8"],
                                parent="buyer_details")

        self.get_text_value(field_name="buyer_province_state",
                            source_doc=self.additional_fields_doc,
                            required=False,
                            xml_name="CountrySubentity",
                            min_length=0,
                            max_length=127,
                            rules=["BR-KSA-F-06", "BT-54", "BG-8"],
                            parent="buyer_details")

        if invoice_type == "Standard":
            # TODO: handle the condition for this
            self.get_text_value(field_name="buyer_district",
                                source_doc=self.additional_fields_doc,
                                required=False,
                                xml_name="city_subdivision_name",
                                min_length=0,
                                max_length=127,
                                rules=["BR-KSA-63", "BR-KSA-F-06", "KSA-4", "BG-8"],
                                parent="buyer_details")

        elif invoice_type == "Simplified":
            self.get_text_value(field_name="buyer_district",
                                source_doc=self.additional_fields_doc,
                                required=False,
                                xml_name="city_subdivision_name",
                                min_length=0,
                                max_length=127,
                                rules=["BR-KSA-63", "BR-KSA-F-06", "KSA-4", "BG-8"],
                                parent="buyer_details")

        if invoice_type == "Standard":
            self.get_text_value(field_name="buyer_country_code",
                                source_doc=self.additional_fields_doc,
                                required=True,
                                xml_name="identification_code",
                                rules=["BR-KSA-10", "BR-KSA-63", "BR-CL-14", "BR-10", "BT-55", "BG-8"],
                                parent="buyer_details")

        elif invoice_type == "Simplified":
            self.get_text_value(field_name="buyer_country_code",
                                source_doc=self.additional_fields_doc,
                                required=False,
                                xml_name="identification_code",
                                rules=["BR-KSA-10", "BR-KSA-63", "BR-CL-14", "BR-10", "BT-55", "BG-8"],
                                parent="buyer_details")

        if invoice_type == "Standard":
            # TODO: handle conditional
            self.get_text_value(field_name="buyer_vat_registration_number",
                                source_doc=self.additional_fields_doc,
                                required=True,
                                xml_name="company_id",
                                rules=["BR-KSA-44", "BR-KSA-46", "BT-48", "BG-7"],
                                parent="buyer_details")

        elif invoice_type == "Simplified":
            self.get_text_value(field_name="buyer_vat_registration_number",
                                source_doc=self.additional_fields_doc,
                                required=False,
                                xml_name="company_id",
                                rules=["BR-KSA-44", "BR-KSA-46", "BT-48", "BG-7"],
                                parent="buyer_details")

        if invoice_type == "Standard":
            self.get_text_value(field_name="customer_name",
                                source_doc=self.sales_invoice_doc,
                                required=True,
                                xml_name="registration_name",
                                min_length=1,
                                max_length=1000,
                                rules=["BR-KSA-25", "BR-KSA-42", "BR-KSA-71", "BR-KSA-F-06", "BT-44", "BG-7"],
                                parent="buyer_details")

        elif invoice_type == "Simplified" and self.sales_invoice_doc.get("customer_name"):
            self.get_text_value(field_name="customer_name",
                                source_doc=self.sales_invoice_doc,
                                required=False,
                                xml_name="registration_name",
                                min_length=0,
                                max_length=1000,
                                rules=["BR-KSA-25", "BR-KSA-42", "BR-KSA-71", "BR-KSA-F-06", "BT-44", "BG-7"],
                                parent="buyer_details")

        # --------------------------- END Buyer Details fields ------------------------------

    def get_e_invoice_details(self):
        # --------------------------- START Invoice fields ------------------------------
        # --------------------------- START Invoice Basic info ------------------------------
        self.get_text_value(field_name="name",
                            source_doc=self.sales_invoice_doc,
                            required=True,
                            xml_name="id",
                            rules=["BT-1", "BR-02", "BR-KSA-F-06"],
                            parent="invoice")

        self.get_text_value(field_name="uuid",
                            source_doc=self.additional_fields_doc,
                            required=True,
                            xml_name="uuid",
                            rules=["KSA-1", "BR-KSA-03"],
                            parent="invoice")

        self.get_date_value(field_name="posting_date",
                            source_doc=self.sales_invoice_doc,
                            required=True,
                            xml_name="issue_date",
                            rules=["BT-2", "BR-03", "BR-KSA-04", "BR-KSA-F-01"],
                            parent="invoice")

        self.get_time_value(field_name="posting_time",
                            source_doc=self.sales_invoice_doc,
                            required=True,
                            xml_name="issue_time",
                            rules=["KSA-25", "BR-KSA-70"],
                            parent="invoice")

        self.get_text_value(field_name="invoice_type_code",
                            source_doc=self.additional_fields_doc,
                            required=True,
                            xml_name="invoice_type_code",
                            rules=["BT-3", "BR-04", "BR-CL-01", "BR-KSA-05"],
                            parent="invoice")

        self.get_text_value(field_name="invoice_type_transaction",
                            source_doc=self.additional_fields_doc,
                            required=True,
                            xml_name="invoice_type_transaction",
                            rules=["KSA-2", "BR-KSA-06", "BR-KSA-07", "BR-KSA-31"],
                            parent="invoice")

        self.get_text_value(field_name="currency",
                            source_doc=self.sales_invoice_doc,
                            required=True,
                            xml_name="currency_code",
                            rules=["BT-5", "BR-05", "BR-CL-04", "BR-KSA-CL-02"],
                            parent="invoice")
        # Default "SAR"
        self.get_text_value(field_name="tax_currency",
                            source_doc=self.sales_invoice_doc,
                            required=True,
                            xml_name="tax_currency",
                            rules=["BT-6", "BR-CL-05", "BR-KSA-EN16931-02", "BR-KSA-68"],
                            parent="invoice")

        self.get_text_value(field_name="invoice_counter",
                            source_doc=self.additional_fields_doc,
                            required=True,
                            xml_name="invoice_counter_value",
                            rules=["KSA-16", "BR-KSA-33", "BR-KSA-34"],
                            parent="invoice")

        self.get_text_value(field_name="previous_invoice_hash",
                            source_doc=self.additional_fields_doc,
                            required=True,
                            xml_name="previous_invoice_hash",
                            rules=["KSA-13", "BR-KSA-26", "BR-KSA-61"],
                            parent="invoice")

        self.get_text_value(field_name="qr_code",
                            source_doc=self.additional_fields_doc,
                            required=True,
                            xml_name="qr_code",
                            rules=["KSA-14", "BR-KSA-27"],
                            parent="invoice")
        self.get_text_value(field_name="crypto_graphic_stamp",
                            source_doc=self.additional_fields_doc,
                            required=True,
                            xml_name="crypto_graphic_stamp",
                            rules=[" KSA-15", "Digital Identity Standards", "BR-KSA-28", "BR-KSA-29", "BR-KSA-30",
                                   "BR-KSA-60"],
                            parent="invoice")

        # TODO: Purchasing Order Exists
        # TODO: Billing Reference if the invoice is credit or debit (return against field)
        # FIXME: Contracting (contract ID)
        if self.sales_invoice_doc.get("contract_id"):
            self.get_text_value(field_name="contract_id",
                                source_doc=self.sales_invoice_doc,
                                required=False,
                                xml_name="contract_id",
                                rules=["BT-12", "BR-KSA-F-06"],
                                parent="invoice")

        self.get_float_value(field_name="total",
                             source_doc=self.sales_invoice_doc,
                             required=True,
                             xml_name="total",
                             rules=["BG-22", "BT-106", "BR-CO-10", "BR-DEC-09", "2"],
                             parent="invoice")

        self.get_float_value(field_name="net_total",
                             source_doc=self.sales_invoice_doc,
                             required=True,
                             xml_name="net_total",
                             rules=["BG-22", "BT-109", "BR-13", "BR-CO-13", "BR-DEC-12", "BR-KSA-F-04"],
                             parent="invoice")

        self.get_float_value(field_name="total_taxes_and_charges",
                             source_doc=self.sales_invoice_doc,
                             required=True,
                             xml_name="total_taxes_and_charges",
                             rules=["BG-22", "BT-110", "BR-CO-14", "BR-DEC-13", "BR-KSA-EN16931-08",
                                    "BR-KSA-EN16931-09",
                                    "BR-KSA-F-04"],
                             parent="invoice")
        # TODO: Tax Account Currency
        self.get_float_value(field_name="grand_total",
                             source_doc=self.sales_invoice_doc,
                             required=True,
                             xml_name="grand_total",
                             rules=["BG-22", "BT-112", "BR-14", "BR-CO-15", "BR-DEC-14", "BR-KSA-F-04"],
                             parent="invoice")

        self.get_float_value(field_name="rounding_adjustment",
                             source_doc=self.sales_invoice_doc,
                             required=False,
                             xml_name="rounding_adjustment",
                             rules=["BG-22", "BT-114", "BR-DEC-17"],
                             parent="invoice")

        self.get_float_value(field_name="outstanding_amount",
                             source_doc=self.sales_invoice_doc,
                             required=False,
                             xml_name="outstanding_amount",
                             rules=["BG-22", "BT-115", "BR-15", "BR-CO-16", "BR-DEC-18"],
                             parent="invoice")
        # --------------------------- END Invoice Basic info ------------------------------
        # --------------------------- Start Getting Invoice's item lines ------------------------------
        # TODO : Add Rules for fields
        item_lines = []
        for item in self.sales_invoice_doc.get("items"):
            new_item = {}
            req_fields = ["idx", "qty", "uom", "item_name", "net_amount", "amount", "price_list_rate", "rate"]
            for it in req_fields:
                if it not in ["item_name", "uom"]:
                    new_item[it] = self.get_float_value(
                        field_name=it,
                        source_doc=item,
                        required=True,
                        xml_name=it
                    )
                elif it in ["item_name", "uom"]:
                    new_item[it] = self.get_text_value(
                        field_name=it,
                        source_doc=item,
                        required=True,
                        xml_name=it
                    )
            item_lines.append(new_item)

        self.result["invoice"]["item_lines"] = item_lines
        # --------------------------- END Getting Invoice's item lines ------------------------------
