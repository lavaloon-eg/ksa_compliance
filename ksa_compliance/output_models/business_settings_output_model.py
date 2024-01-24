import frappe
from ksa_compliance.output_models.e_invoice_model import MappingModel, InputModelAttribute


def get_sales_invoice_by_id(invoice_id: str):
    return frappe.get_doc("Sales Invoice", invoice_id)


def get_business_settings_doc(company_id: str):
    co = frappe.get_doc("Company", company_id)
    print(co.as_dict())
    co.get("company")+'-'+co.get("country")+'-'+co.get("currency")
    return


class Einvoice:
    # TODO:
    # get Sales Invoice Doc
    # get Business Settings Doc
    # if batch doc = none validate business settings else pass

    # Any parameter won't be passed to InputModelAttribute it will be assigned with its default value
    def __init__(self, sales_invoice_additional_fields_doc, invoice_type: str, batch_doc=None):

        print(sales_invoice_additional_fields_doc, invoice_type)
        self.additional_fields = sales_invoice_additional_fields_doc

        self.batch_doc = batch_doc
        # self.invoice_type = invoice_type
        self.result = {}
        self.error_dic = {}

        self.sales_invoice_doc = get_sales_invoice_by_id(
            invoice_id=sales_invoice_additional_fields_doc.get("sales_invoice"))

        print(self.sales_invoice_doc.as_dict())
        sl = self.sales_invoice_doc
        print(sl.get("company")+'-'+sl.get("country")+'-'+sl.get("currency"))
        asd
        # TODO: Set the appropriate filters for business settings
        self.business_settings_doc = get_business_settings_doc(
            business_settings_id=self.additional_fields['business_settings_id'])

        # Start Business Settings fields

        # TODO: special validations handling
        party_types = ("CRN", "MOM", "MLS", "700", "SAG", "OTH")
        self.get_dict_value(field_name="party_identification",
                            source_doc=self.business_settings_doc,
                            required=True,
                            xml_name="party_identification",
                            rules=["BR-KSA-08", "BT-29", "BT-29-1", "BG-5"])

        self.get_text_value(field_name="street_name",
                            source_doc=self.business_settings_doc,
                            required=True,
                            xml_name="street_name",
                            min_length=1,
                            max_length=127,
                            rules=["BR-KSA-09", "BR-KSA-F-06", "BR-08", "BT-35", "BG-5"])

        self.get_text_value(field_name="additional_street_name",
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

        self.get_text_value(field_name="additional_address_number",
                            source_doc=self.business_settings_doc,
                            required=False,
                            xml_name="plot_identification",
                            rules=["BR-08", "KSA-23", "BG-5"])

        self.get_text_value(field_name="city_name",
                            source_doc=self.business_settings_doc,
                            required=True,
                            xml_name="city_name",
                            rules=["BR-KSA-09", "BR-KSA-F-06", "BR-08", "BT-37", "BG-5"])

        self.get_text_value(field_name="postal_code",
                            source_doc=self.business_settings_doc,
                            required=True,
                            xml_name="postal_zone",
                            rules=["BR-KSA-09", "BR-KSA-66", "BR-08", "BT-38", "BG-5"])

        self.get_text_value(field_name="province_state",
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

        self.get_text_value(field_name="VatRegistrationNumber",
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

        # TODO
        self.get_dict_value(field_name="other_buyer_identification",
                            source_doc=self.sales_invoice_doc,
                            required=True,
                            xml_name="PartyIdentification",
                            rules=["BR-KSA-08", "BT-29", "BT-29-1", "BG-5"])

        if type == "standard":
            self.get_text_value(field_name="buyer_street_name",
                                source_doc=self.sales_invoice_doc,
                                required=True,
                                xml_name="street_name",
                                min_length=1,
                                max_length=127,
                                rules=["BR-KSA-10", "BR-KSA-63", "BR-KSA-F-06", "BR-10", "BT-50", "BG-8"])
        elif type == "simplified":
            self.get_text_value(field_name="buyer_street_name",
                                source_doc=self.sales_invoice_doc,
                                required=False,
                                xml_name="street_name",
                                min_length=0,
                                max_length=127,
                                rules=["BR-KSA-10", "BR-KSA-63", "BR-KSA-F-06", "BR-10", "BT-50", "BG-8"])

        self.get_text_value(field_name="buyer_additional_street_name",
                            source_doc=self.sales_invoice_doc,
                            required=False,
                            xml_name="additional_street_name",
                            min_length=0,
                            max_length=127,
                            rules=["BR-KSA-F-06", "BT-51", "BG-8"])

        # TODO
        # self.get_text_value(field_name="buyer_building_number",
        #                     source_doc=self.sales_invoice_doc,
        #                     required=True,
        #                     xml_name="building_number",
        #                     rules=["KSA-18", "BG-8"])

        self.get_text_value(field_name="buyer_additional_address_number",
                            source_doc=self.sales_invoice_doc,
                            required=False,
                            xml_name="plot_identification",
                            rules=["KSA-19", "BG-8"])

        if type == "Standard":
            self.get_text_value(field_name="buyer_city_name",
                                source_doc=self.sales_invoice_doc,
                                required=True,
                                xml_name="city_name",
                                min_length=1,
                                max_length=127,
                                rules=["BR-KSA-10", "BR-KSA-63", "BR-KSA-F-06", "BR-10", "BT-52", "BG-8"])
        elif type == "simplified":
            self.get_text_value(field_name="buyer_city_name",
                                source_doc=self.sales_invoice_doc,
                                required=False,
                                xml_name="city_name",
                                min_length=0,
                                max_length=127,
                                rules=["BR-KSA-10", "BR-KSA-63", "BR-KSA-F-06", "BR-10", "BT-52", "BG-8"])

        if type == "Standard":
            pass
            # TODO
            # self.get_text_value(field_name="postal_code",
            #                     source_doc=self.business_settings_doc,
            #                     required=True,
            #                     xml_name="postal_zone",
            #                     rules=["BR-KSA-09", "BR-KSA-66", "BR-08", "BT-38", "BG-5"])
        elif type == "Simplified":
            self.get_text_value(field_name="buyer_postal_code",
                                source_doc=self.sales_invoice_doc,
                                required=False,
                                xml_name="postal_zone",
                                rules=["BR-10", "BT-53", "BG-8"])

        self.get_text_value(field_name="buyer_province_state",
                            source_doc=self.sales_invoice_doc,
                            required=False,
                            xml_name="CountrySubentity",
                            min_length=0,
                            max_length=127,
                            rules=["BR-KSA-F-06", "BT-54", "BG-8"])

        if type == "Standard":
            pass
            # TODO
            # self.get_text_value(field_name="buyer_district",
            #                     source_doc=self.business_settings_doc,
            #                     required=True,
            #                     xml_name="city_subdivision_name",
            #                     min_length=1,
            #                     max_length=127,
            #                     rules=["BR-KSA-63", "BR-KSA-F-06", "KSA-4", "BG-8"])
        elif type == "Simplified":
            self.get_text_value(field_name="buyer_district",
                                source_doc=self.sales_invoice_doc,
                                required=False,
                                xml_name="city_subdivision_name",
                                min_length=0,
                                max_length=127,
                                rules=["BR-KSA-63", "BR-KSA-F-06", "KSA-4", "BG-8"])

        if type == "Standard":
            self.get_text_value(field_name="buyer_district",
                                source_doc=self.sales_invoice_doc,
                                required=False,
                                xml_name="city_subdivision_name",
                                min_length=0,
                                max_length=127,
                                rules=["BR-KSA-63", "BR-KSA-F-06", "KSA-4", "BG-8"])

        elif type == "Simplified":
            self.get_text_value(field_name="buyer_district",
                                source_doc=self.sales_invoice_doc,
                                required=False,
                                xml_name="city_subdivision_name",
                                min_length=0,
                                max_length=127,
                                rules=["BR-KSA-63", "BR-KSA-F-06", "KSA-4", "BG-8"])

        if type == "Standard":
            self.get_text_value(field_name="buyer_country_code",
                                source_doc=self.sales_invoice_doc,
                                required=True,
                                xml_name="identification_code",
                                rules=["BR-KSA-10", "BR-KSA-63", "BR-CL-14", "BR-10", "BT-55", "BG-8"])

        elif type == "Simplified":
            self.get_text_value(field_name="buyer_country_code",
                                source_doc=self.sales_invoice_doc,
                                required=False,
                                xml_name="identification_code",
                                rules=["BR-KSA-10", "BR-KSA-63", "BR-CL-14", "BR-10", "BT-55", "BG-8"])

    def get_text_value(self, field_name: str, source_doc, required: bool, xml_name: str = None,
                       min_length: int = 0, max_length: int = 5000, rules: list = None):

        if required and field_name not in source_doc:
            self.error_dic[field_name] = f"Missing field"
            return

        field_value = source_doc.get(field_name).trim() if source_doc.get(field_name) else None

        if required and field_value is None:
            self.error_dic[field_name] = f"Missing field value: {field_name}."
            return

        if not min_length <= len(field_value) <= max_length:
            self.error_dic[field_name] = f'Invalid {field_name} field size value {len(field_value)}'
            return

        field_name = xml_name if xml_name else field_name
        self.result[field_name] = field_value
        return field_value

    def get_int_value(self, field_name: str, source_doc, required: bool, min_value: int,
                      max_value: int, xml_name: str = None, rules: list = None):
        if required and field_name not in source_doc:
            self.error_dic[field_name] = f"Missing field"
            return

        field_value = source_doc.get(field_name, None)

        if required and field_value is None:
            self.error_dic[field_name] = f"Missing field value: {field_name}."
            return

        if not min_value <= field_value <= max_value:
            self.error_dic[field_name] = f'field value must be between {min_value} and {max_value}'
            return

        field_name = xml_name if xml_name else field_name
        self.result[field_name] = field_value
        return field_value

    def get_float_value(self, field_name: str, source_doc, required: bool, min_value: int,
                        max_value: int, xml_name: str = None, rules: list = None):
        if required and field_name not in source_doc:
            self.error_dic[field_name] = f"Missing field"
            return

        field_value = source_doc.get(field_name, None)

        # Try to parse
        field_value = float(field_value) if type(field_value) is int else field_value

        if required and field_value is None:
            self.error_dic[field_name] = f"Missing field value: {field_name}."
            return

        if not min_value <= field_value <= max_value:
            self.error_dic[field_name] = f'field value must be between {min_value} and {max_value}'
            return

        field_name = xml_name if xml_name else field_name
        self.result[field_name] = field_value
        return field_value

    def get_dict_value(self, field_name: str, source_doc, required: bool, xml_name: str = None, rules: list = None):
        if required and field_name not in source_doc:
            self.error_dic[field_name] = f"Missing field"
            return

        field_value = source_doc.get(field_name, None)

        if required and (field_value is None or {}):
            self.error_dic[field_name] = f"Missing field value: {field_name}."
            return

        field_name = xml_name if xml_name else field_name
        self.result[field_name] = field_value
        return field_value

    def get_list_value(self, field_name: str, source_doc, required: bool, xml_name: str = None, rules: list = None):
        if required and field_name not in source_doc:
            self.error_dic[field_name] = f"Missing field"
            return

        field_value = source_doc.get(field_name, None)

        if required and (field_value is None or []):
            self.error_dic[field_name] = f"Missing field value: {field_name}."
            return

        field_name = xml_name if xml_name else field_name
        self.result[field_name] = field_value
        return field_value

    # TODO: Complete the implementation
    def validate_scheme_with_order(self, att_key, att_value, valid_scheme_ids, source_property=""):
        if isinstance(att_value, dict):
            rem_scheme_ids = valid_scheme_ids

            for scheme_id, scheme_value in att_value.items():
                if scheme_id not in valid_scheme_ids:
                    self.result.pop(att_key)
                    self.error_dic['party_identification'] = f"Invalid scheme ID: {scheme_id} for Seller Additional IDs"
                    return False
                elif scheme_id not in rem_scheme_ids:
                    self.result.pop(att_key)
                    self.error_dic['party_identification'] = (
                        f"Invalid scheme ID Order: "
                        f"for {att_value} in {source_property} Additional IDs")
                    return False
                else:
                    index = rem_scheme_ids.index(scheme_id)
                    rem_scheme_ids = rem_scheme_ids[index:]
            return True
        else:
            self.result.pop(att_key)
            self.error_dic[att_key] = "Invalid data type, expecting a list of tuples"
            return False

    def get_customer_address_details(self, invoice_id):
        pass

    def get_customer_info(self, invoice_id):
        pass
