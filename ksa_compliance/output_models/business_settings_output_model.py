import frappe
from ksa_compliance.output_models.e_invoice_model import MappingModel, InputModelAttribute


def get_sales_invoice_by_id(invoice_id: str):
    return frappe.get_doc("Sales Invoice", invoice_id).as_dict()


def get_business_settings_doc(company_id: str):
    company_doc = frappe.get_doc("Company", company_id)
    business_settings_id = company_id + '-' + company_doc.get("country") + '-' + company_doc.get("default_currency")
    return frappe.get_doc("ZATCA Business Settings", business_settings_id).as_dict()


class Einvoice:
    # TODO:
    # get Sales Invoice Doc
    # get Business Settings Doc
    # if batch doc = none validate business settings else pass

    # Any parameter won't be passed to InputModelAttribute it will be assigned with its default value
    def __init__(self, sales_invoice_additional_fields_doc, invoice_type: str = "Simplified", batch_doc=None):

        self.additional_fields_doc = sales_invoice_additional_fields_doc.as_dict()
        self.batch_doc = batch_doc
        self.result = {}
        self.error_dic = {}

        self.sales_invoice_doc = get_sales_invoice_by_id(
            invoice_id=sales_invoice_additional_fields_doc.get("sales_invoice"))

        self.business_settings_doc = get_business_settings_doc(company_id=self.sales_invoice_doc.get("company"))

        # Start Business Settings fields

        # TODO: special validations handling
        self.get_dict_value(field_name="other_ids",
                            source_doc=self.business_settings_doc,
                            required=True,
                            xml_name="party_identification",
                            rules=["BR-KSA-08", "BT-29", "BT-29-1", "BG-5"])

        self.get_text_value(field_name="street",
                            source_doc=self.business_settings_doc,
                            required=True,
                            xml_name="street_name",
                            min_length=1,
                            max_length=127,
                            rules=["BR-KSA-09", "BR-KSA-F-06", "BR-08", "BT-35", "BG-5"])

        self.get_text_value(field_name="additional_street",
                            source_doc=self.business_settings_doc,
                            required=False,
                            xml_name="additional_street_name",
                            min_length=0,
                            max_length=127,
                            rules=["BR-KSA-F-06", "BR-08", "BT-36", "BG-5"])

        self.get_text_value(field_name="building_number",
                            source_doc=self.business_settings_doc,
                            required=True,
                            xml_name="building_number",
                            rules=["BR-KSA-09", "BR-KSA-37", "BR-08", "KSA-17", "BG-5"])

        self.get_text_value(field_name="additional_address_number",  # TODO: Fix missing field
                            source_doc=self.business_settings_doc,
                            required=False,
                            xml_name="plot_identification",
                            rules=["BR-08", "KSA-23", "BG-5"])

        self.get_text_value(field_name="city",
                            source_doc=self.business_settings_doc,
                            required=True,
                            xml_name="city_name",
                            rules=["BR-KSA-09", "BR-KSA-F-06", "BR-08", "BT-37", "BG-5"])

        self.get_text_value(field_name="postal_code",
                            source_doc=self.business_settings_doc,
                            required=True,
                            xml_name="postal_zone",
                            rules=["BR-KSA-09", "BR-KSA-66", "BR-08", "BT-38", "BG-5"])

        self.get_text_value(field_name="province_state",  # TODO: Fix missing field
                            source_doc=self.business_settings_doc,
                            required=False,
                            xml_name="CountrySubentity",
                            min_length=0,
                            max_length=127,
                            rules=["BR-KSA-F-06", "BR-08", "BT-39", "BG-5"])

        self.get_text_value(field_name="district",
                            source_doc=self.business_settings_doc,
                            required=True,
                            xml_name="city_subdivision_name",
                            min_length=1,
                            max_length=127,
                            rules=["BR-KSA-09", "BR-KSA-F-06", "BR-08", "KSA-3", "BG-5"])

        # Field country code will be hardcoded in xml with value "SA"

        self.get_text_value(field_name="vat_registration_number",
                            source_doc=self.business_settings_doc,
                            required=True,
                            xml_name="company_id",
                            rules=["BR-KSA-39", "BR-KSA-40", "BT-31", "BG-5"])

        self.get_text_value(field_name="seller_name",
                            source_doc=self.business_settings_doc,
                            required=True,
                            xml_name="registration_name",
                            min_length=1,
                            max_length=1000,
                            rules=["BR-KSA-F-06", "BR-06", "BT-27", "BG-5"])

        # End Business Settings fields
        # Start Sales Invoice fields

        self.get_dict_value(field_name="other_buyer_identification",  # TODO: Fix Add to doctype customer and additional
                            source_doc=self.sales_invoice_doc,
                            required=True,
                            xml_name="PartyIdentification",
                            rules=["BR-KSA-08", "BT-29", "BT-29-1", "BG-5"])

        if invoice_type == "Standard":
            self.get_text_value(field_name="buyer_street_name",
                                source_doc=self.additional_fields_doc,
                                required=True,
                                xml_name="street_name",
                                min_length=1,
                                max_length=127,
                                rules=["BR-KSA-10", "BR-KSA-63", "BR-KSA-F-06", "BR-10", "BT-50", "BG-8"])
        elif invoice_type == "Simplified":
            self.get_text_value(field_name="buyer_street_name",
                                source_doc=self.additional_fields_doc,
                                required=False,
                                xml_name="street_name",
                                min_length=0,
                                max_length=127,
                                rules=["BR-KSA-10", "BR-KSA-63", "BR-KSA-F-06", "BR-10", "BT-50", "BG-8"])

        self.get_text_value(field_name="buyer_additional_street_name",
                            source_doc=self.additional_fields_doc,
                            required=False,
                            xml_name="additional_street_name",
                            min_length=0,
                            max_length=127,
                            rules=["BR-KSA-F-06", "BT-51", "BG-8"])

        self.get_text_value(field_name="buyer_building_number",
                            source_doc=self.additional_fields_doc,
                            required=False,
                            xml_name="building_number",
                            rules=["KSA-18", "BG-8"])

        self.get_text_value(field_name="buyer_additional_number",
                            # TODO: add additional number field for address if needed
                            source_doc=self.additional_fields_doc,
                            required=False,
                            xml_name="plot_identification",
                            rules=["KSA-19", "BG-8"])

        if invoice_type == "Standard":
            self.get_text_value(field_name="buyer_city",
                                source_doc=self.additional_fields_doc,
                                required=True,
                                xml_name="city_name",
                                min_length=1,
                                max_length=127,
                                rules=["BR-KSA-10", "BR-KSA-63", "BR-KSA-F-06", "BR-10", "BT-52", "BG-8"])
        elif invoice_type == "Simplified":
            self.get_text_value(field_name="buyer_city",
                                source_doc=self.additional_fields_doc,
                                required=False,
                                xml_name="city_name",
                                min_length=0,
                                max_length=127,
                                rules=["BR-KSA-10", "BR-KSA-63", "BR-KSA-F-06", "BR-10", "BT-52", "BG-8"])

        if invoice_type == "Standard":
            pass
            # TODO
            # self.get_text_value(field_name="postal_code",
            #                     source_doc=self.business_settings_doc,
            #                     required=True,
            #                     xml_name="postal_zone",
            #                     rules=["BR-KSA-09", "BR-KSA-66", "BR-08", "BT-38", "BG-5"])
        elif invoice_type == "Simplified":
            self.get_text_value(field_name="buyer_postal_code",
                                source_doc=self.additional_fields_doc,
                                required=False,
                                xml_name="postal_zone",
                                rules=["BR-10", "BT-53", "BG-8"])

        self.get_text_value(field_name="buyer_province_state",
                            source_doc=self.additional_fields_doc,
                            required=False,
                            xml_name="CountrySubentity",
                            min_length=0,
                            max_length=127,
                            rules=["BR-KSA-F-06", "BT-54", "BG-8"])

        if invoice_type == "Standard":
            # TODO: handle the condition for this
            self.get_text_value(field_name="buyer_district",
                                source_doc=self.additional_fields_doc,
                                required=False,
                                xml_name="city_subdivision_name",
                                min_length=0,
                                max_length=127,
                                rules=["BR-KSA-63", "BR-KSA-F-06", "KSA-4", "BG-8"])

        elif invoice_type == "Simplified":
            self.get_text_value(field_name="buyer_district",
                                source_doc=self.additional_fields_doc,
                                required=False,
                                xml_name="city_subdivision_name",
                                min_length=0,
                                max_length=127,
                                rules=["BR-KSA-63", "BR-KSA-F-06", "KSA-4", "BG-8"])

        if invoice_type == "Standard":
            self.get_text_value(field_name="buyer_country_code",
                                source_doc=self.additional_fields_doc,
                                required=True,
                                xml_name="identification_code",
                                rules=["BR-KSA-10", "BR-KSA-63", "BR-CL-14", "BR-10", "BT-55", "BG-8"])

        elif invoice_type == "Simplified":
            self.get_text_value(field_name="buyer_country_code",
                                source_doc=self.additional_fields_doc,
                                required=False,
                                xml_name="identification_code",
                                rules=["BR-KSA-10", "BR-KSA-63", "BR-CL-14", "BR-10", "BT-55", "BG-8"])

    def get_text_value(self, field_name: str, source_doc: dict, required: bool, xml_name: str = None,
                       min_length: int = 0, max_length: int = 5000, rules: list = None):
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
        self.result[field_name] = field_value
        return field_value

    def get_int_value(self, field_name: str, source_doc: dict, required: bool, min_value: int,
                      max_value: int, xml_name: str = None, rules: list = None):
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
        self.result[field_name] = field_value
        return field_value

    def get_float_value(self, field_name: str, source_doc: dict, required: bool, min_value: int,
                        max_value: int, xml_name: str = None, rules: list = None):
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
        self.result[field_name] = field_value
        return field_value

    def get_dict_value(self, field_name: str, source_doc: dict, required: bool, xml_name: str = None,
                       rules: list = None):
        if required and field_name not in source_doc:
            self.error_dic[field_name] = f"Missing field"
            return

        field_value = source_doc.get(field_name)
        if required and (field_value is None or {}):
            self.error_dic[field_name] = f"Missing field value: {field_name}."
            return
        if field_value is None or {}:
            return

        if field_name == 'party_identification':
            party_list = ["CRN", "MOM", "MLS", "700", "SAG", "OTH"]
            valid = self.validate_scheme_with_order(field_value=field_value, ordered_list=party_list)
            if not valid:
                self.error_dic[field_name] = f"Wrong ordered for field: {field_name}."
                return

        field_name = xml_name if xml_name else field_name
        self.result[field_name] = field_value
        return field_value

    def get_list_value(self, field_name: str, source_doc: dict, required: bool, xml_name: str = None,
                       rules: list = None):
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
        self.result[field_name] = field_value
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
