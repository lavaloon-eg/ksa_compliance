import frappe
from ksa_compliance.e_invoice_model import MappingModel, InputModelAttribute


class BusinessSettingsInputModel():

    def __init__(self):
        # print(business_settings)
        business_settings = {"party_identification": "party1", "street_name": "street1", "test": "maged"}
        super().__init__(business_settings)

    @classmethod
    def initialize_with_example(cls):

        # business_settings_data = {"key1": "value1", "key2": "value2"}
        # mapping_data = {"mapping_key": "mapping_value"}
        # accounting_party = AccountingSupplierParty(business_settings=business_settings)
        business_settings = {"party_identification": "party1", "street_name": "street1", "test": "maged"}

        return cls(business_settings=business_settings)

    #    class validation methods

    def validate_scheme_with_order(self, value, valid_scheme_ids, source_property):
        if isinstance(value, list):
            rem_scheme_ids = valid_scheme_ids

            for scheme_id, scheme_value in value:
                if scheme_id not in valid_scheme_ids:
                    self.error_dic[
                        'party_identification'] = f"Invalid scheme ID: {scheme_id} for Seller Additional IDs"
                    return False
                elif scheme_id not in rem_scheme_ids:
                    self.error_dic['party_identification'] = (f"Invalid scheme ID Order: "
                                                              f"for {value} in {source_property} Additional IDs")
                    return False
                else:
                    index = rem_scheme_ids.index(scheme_id)
                    rem_scheme_ids = rem_scheme_ids[index:]
            return True
        else:
            self.error_dic['party_identification'] = "Invalid data type, expecting a list of tuples"
            return False

    def validate_string(self, value, field_name):
        if isinstance(value, str):
            return value
        else:
            self.error_dic[field_name] = "Invalid data type. Must be a non-None string."
            return None

    def validate_optional_string(self, value, field_name):
        if isinstance(value, str) or value is None:
            return value
        else:
            self.error_dic[field_name] = "Invalid data type. Must be a non-None string."
            return None


class BusinessSettingsOutputModel(MappingModel):
    party_identification = InputModelAttribute(attr_type=str, required=True, min_len=1, max_len=1000)
    street_name = InputModelAttribute(attr_type=str, required=True, min_len=0, max_len=172)
    additional_street_name = InputModelAttribute(attr_type=str, required=False, min_len=0, max_len=172)
    building_number = InputModelAttribute(attr_type=str, required=True)
    additional_number = InputModelAttribute(attr_type=str, required=False)
    city_name = InputModelAttribute(attr_type=str, required=True, min_len=0, max_len=172)
    postal_code = InputModelAttribute(attr_type=str, required=True)
    province = InputModelAttribute(attr_type=str, required=False, min_len=0, max_len=172)
    district = InputModelAttribute(attr_type=str, required=True, min_len=0, max_len=172)


@frappe.whitelist(allow_guest=True)
def generate_xml():
    import lxml.etree as ET
    import json
    data = frappe.request.data or {}
    # if isinstance(data, str):
    data = json.loads(data)

    # business_settings_instance = frappe.get_doc("ZATCA Business Settings", "lavaloon-Egypt-EGP").as_dict()
    business_settings_instance = data
    print("input business_settings_instance", business_settings_instance)

    # Construct output model
    final_result = BusinessSettingsOutputModel(data=business_settings_instance)

    # print("\n\n\n", final_result.party_identification, "\n\n\n")
    print("\n\n\n", final_result.data, "\n\n\n")
    return final_result.result, final_result.error_dic
    # parser = ET.XMLParser(recover=True)
    # party_identification = [
    #     ("CRN", "324223432432432"),
    #     ("MOM", "324223432432432"),
    #     ("MLS", "324223432432432"),
    #     ("700", "324223432432432"),
    #     ("SAG", "324223432432432"),
    #     ("OTH", "324223432432432")]

    # street_name = "street name address"
    # building_number = "3242"
    # business_settings = {"party_identification": "party1", "street_name": "street1"}

    # accounting_party = AccountingSupplierParty(business_settings=business_settings)

    # print(accounting_party)
    # print(accounting_party.party_identification)
    # # Check for errors
    # print(accounting_party.error_dic)

    # xml_template = f"""
    # <cac:AccountingSupplierParty>
    #     <cac:Party>
    #         <cac:PartyIdentification>
    #             <cbc:ID schemeID="CRN">{accounting_party.party_identification}</cbc:ID>
    #         </cac:PartyIdentification>
    #         <cac:PostalAddress>
    #             <cbc:StreetName>{accounting_party.street_name}</cbc:StreetName>
    #         </cac:PostalAddress>
    #     </cac:Party>
    # </cac:AccountingSupplierParty>
    # """
    # tree = ET.ElementTree(ET.fromstring(xml_template, parser=parser))

    # return accounting_party.error_dic
