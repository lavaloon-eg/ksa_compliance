import frappe


class AccountingSupplierParty:
    def __init__(self):
        self.error_dic = {}
        self.party_identification = ""
        self.street_name = ""
        self.building_number = ""

    @property
    def party_identification(self):
        return self._party_identification

    @party_identification.setter
    def party_identification(self, value):
        if isinstance(value, str):
            self._party_identification = value
        else:
            self.error_dic['party_identification'] = "Invalid data type"

    @property
    def street_name(self):
        return self._street_name

    @street_name.setter
    def street_name(self, value):
        self._street_name = value

    @property
    def building_number(self):
        return self._building_number

    @building_number.setter
    def building_number(self, value):
        self._building_number = value


@frappe.whitelist(allow_guest=True)
def generate_xml():
    import lxml.etree as ET
    parser = ET.XMLParser(recover=True)
    accounting_party = AccountingSupplierParty()
    accounting_party.party_identification = "324223432432432"
    accounting_party.street_name = "الامير سلطان"
    accounting_party.building_number = "3242"

    xml_template = f"""
    <cac:AccountingSupplierParty>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID schemeID="CRN">{accounting_party.party_identification}</cbc:ID>
            </cac:PartyIdentification>
            <cac:PostalAddress>
                <cbc:StreetName>{accounting_party.street_name}</cbc:StreetName>
                <!-- Add other fields here -->
            </cac:PostalAddress>
            <!-- Add other sections here -->
        </cac:Party>
    </cac:AccountingSupplierParty>
    """
    tree = ET.ElementTree(ET.fromstring(xml_template, parser=parser))

    return xml_template


print(generate_xml())
