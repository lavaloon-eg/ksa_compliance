import frappe
from ksa_compliance.output_models.business_settings_output_model import BusinessSettingsOutputModel


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
