import frappe
from ksa_compliance.output_models.e_invoice_model import MappingModel, InputModelAttribute


class Einvoice:
    # TODO:
    # get Sales Invoice Doc
    # get Business Settings Doc
    # if batch doc = none validate business settings else pass

    # Any parameter won't be passed to InputModelAttribute it will be assigned with its default value
    def __init__(self, sales_invoice_additional_fields_doc, invoice_type: str, batch_doc=None):
        self.additional_fields = sales_invoice_additional_fields_doc
        self.batch_doc = batch_doc
        self.invoice_type = invoice_type
        self.result = {}
        self.error_dic = {}

        self.sales_invoice_doc = self.get_sales_invoice_by_id(invoice_id=self.additional_fields['sales_invoice_id'])
        # TODO: Set the appropriate filters for business settings
        self.business_settings_doc = self.get_business_settings_doc(
            business_settings_id=self.additional_fields['business_settings_id'])

        # Start Business Settings fields

        # TODO: special validations handling
        party_types = ("CRN", "MOM", "MLS", "700", "SAG", "OTH")
        self.party_identification = self.get_dict_value(field_name="party_identification",
                                                        source_doc=self.business_settings_doc,
                                                        required=True, xml_name="party_identification")

        self.street_name = self.get_text_value(field_name="street_name", source_doc=self.business_settings_doc,
                                               attribute_type=str, required=True, xml_name="street_name",
                                               min_length=1, max_length=127)

        self.building_number = self.get_text_value(field_name="building_number", source_doc=self.business_settings_doc,
                                                   attribute_type=str, required=True, xml_name="building_number")

        self.city_name = self.get_text_value(field_name="city_name", source_doc=self.business_settings_doc,
                                             attribute_type=str, required=True, xml_name="city_name")

        self.postal_code = self.get_text_value(field_name="postal_code", source_doc=self.business_settings_doc,
                                               attribute_type=str, required=True, xml_name="postal_code")

        self.city_subdivision_name = self.get_text_value(field_name="city_subdivision_name",
                                                         source_doc=self.business_settings_doc,
                                                         attribute_type=str, required=True,
                                                         xml_name="city_subdivision_name", min_length=1,
                                                         max_length=127)

        self.identification_code = self.get_text_value(field_name="identification_code",
                                                       source_doc=self.business_settings_doc, attribute_type=str,
                                                       required=True, xml_name="identification_code")

        self.company_id = self.get_text_value(field_name="VatRegistrationNumber", source_doc=self.business_settings_doc,
                                              attribute_type=str, required=False, xml_name="company_id")

        self.registration_name = self.get_text_value(field_name="registration_name",
                                                     source_doc=self.business_settings_doc, attribute_type=str,
                                                     required=False, xml_name="registration_name", min_length=1)
        self.vat_number = self.get_text_value(field_name="vat_number", source_doc=self.business_settings_doc,
                                              attribute_type=str, required=True, xml_name="vat_number")

        self.seller_name = self.get_text_value(field_name="seller_name", source_doc=self.business_settings_doc,
                                               attribute_type=str, required=True, xml_name="seller_name",
                                               min_length=1, max_length=1000)
        # End Business Settings fields

    def get_text_value(self, field_name: str, source_doc, required: bool, xml_name: str = None,
                       min_length: int = 0, max_length: int = 5000):

        if required and field_name not in source_doc:
            self.error_dic[field_name] = f"Missing field"
            return

        field_value = source_doc.get(field_name).trim() if source_doc.get(field_name) else None

        if required and field_value is None:
            self.error_dic[field_name] = f"Missing field value: {field_name}."
            return

        if not min_length <= len(field_value) <= max_length:
            self.error_dic[field_name] = f'Invalid {field_name} field size {len(field_value)}'
            return

        field_name = xml_name if xml_name else field_name
        self.result[field_name] = field_value
        return field_value

    def get_int_value(self, field_name: str, source_doc, required: bool, min_value: int,
                      max_value: int, xml_name: str = None, ):
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
                        max_value: int, xml_name: str = None):
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

    def get_dict_value(self, field_name: str, source_doc, required: bool, xml_name: str = None):
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

    def get_list_value(self, field_name: str, source_doc, required: bool, xml_name: str = None):
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

    def get_sales_invoice_by_id(self, invoice_id: str):
        return frappe.get_doc("Sales Invoice", invoice_id)

    def get_business_settings_doc(self, business_settings_id: str):
        return frappe.get_doc("ZATCA Business Settings", business_settings_id)
