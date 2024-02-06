import json

import frappe
import xml.etree.ElementTree as ET

from frappe.utils import now_datetime, flt


def get_tax_total_from_items(sales_invoice_doc):
    total_tax = 0
    for item in sales_invoice_doc.items:
        item_tax_amount, tax_percent = get_tax_for_item(sales_invoice_doc.taxes[0].item_wise_tax_detail, item.item_code)
        total_tax = total_tax + (item.net_amount * (tax_percent / 100))
    return total_tax


def get_tax_for_item(item_wise_tax_details_str, item):
    # getting tax percentage and tax amount
    data = json.loads(item_wise_tax_details_str)
    tax_percentage = data.get(item, [0, 0])[0]
    tax_amount = data.get(item, [0, 0])[1]
    return tax_amount, tax_percentage


def xml_tags():
    invoice = ET.Element("Invoice", xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2")
    invoice.set("xmlns:cac", "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2")
    invoice.set("xmlns:cbc", "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2")
    invoice.set("xmlns:ext", "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2")
    ubl_extensions = ET.SubElement(invoice, "ext:UBLExtensions")
    ubl_extension = ET.SubElement(ubl_extensions, "ext:UBLExtension")
    extension_uri = ET.SubElement(ubl_extension, "ext:ExtensionURI")
    extension_uri.text = "urn:oasis:names:specification:ubl:dsig:enveloped:xades"
    extension_content = ET.SubElement(ubl_extension, "ext:ExtensionContent")
    ubl_document_signatures = ET.SubElement(extension_content, "sig:UBLDocumentSignatures")
    ubl_document_signatures.set("xmlns:sig", "urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2")
    ubl_document_signatures.set("xmlns:sac",
                                "urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2")
    ubl_document_signatures.set("xmlns:sbc", "urn:oasis:names:specification:ubl:schema:xsd:SignatureBasicComponents-2")
    signature_information = ET.SubElement(ubl_document_signatures, "sac:SignatureInformation")
    signature_id = ET.SubElement(signature_information, "cbc:ID")
    signature_id.text = "urn:oasis:names:specification:ubl:signature:1"
    referenced_signature_id = ET.SubElement(signature_information, "sbc:ReferencedSignatureID")
    referenced_signature_id.text = "urn:oasis:names:specification:ubl:signature:Invoice"
    signature = ET.SubElement(referenced_signature_id, "ds:Signature")
    signature.set("Id", "signature")
    signature.set("xmlns:ds", "http://www.w3.org/2000/09/xmldsig#")
    signed_info = ET.SubElement(signature, "ds:SignedInfo")
    canonicalization_method = ET.SubElement(signed_info, "ds:CanonicalizationMethod")
    canonicalization_method.set("Algorithm", "http://www.w3.org/2006/12/xml-c14n11")
    signature_method = ET.SubElement(signed_info, "ds:SignatureMethod")
    signature_method.set("Algorithm", "http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha256")
    reference = ET.SubElement(signed_info, "ds:Reference")
    reference.set("Id", "invoiceSignedData")
    reference.set("URI", "")
    transforms = ET.SubElement(reference, "ds:Transforms")
    transform = ET.SubElement(transforms, "ds:Transform")
    transform.set("Algorithm", "http://www.w3.org/TR/1999/REC-xpath-19991116")
    xpath = ET.SubElement(transform, "ds:XPath")
    xpath.text = "not(//ancestor-or-self::ext:UBLExtensions)"
    transform2 = ET.SubElement(transforms, "ds:Transform")
    transform2.set("Algorithm", "http://www.w3.org/TR/1999/REC-xpath-19991116")
    xpath2 = ET.SubElement(transform2, "ds:XPath")
    xpath2.text = "not(//ancestor-or-self::cac:Signature)"
    transform3 = ET.SubElement(transforms, "ds:Transform")
    transform3.set("Algorithm", "http://www.w3.org/TR/1999/REC-xpath-19991116")
    xpath3 = ET.SubElement(transform3, "ds:XPath")
    xpath3.text = "not(//ancestor-or-self::cac:AdditionalDocumentReference[cbc:ID='QR'])"
    transform4 = ET.SubElement(transforms, "ds:Transform")
    transform4.set("Algorithm", "http://www.w3.org/2006/12/xml-c14n11")
    digest_method = ET.SubElement(reference, "ds:DigestMethod")
    digest_method.set("Algorithm", "http://www.w3.org/2001/04/xmlenc#sha256")
    digest_value = ET.SubElement(reference, "ds:DigestValue")
    digest_value.text = "O/vEnAxjLAlw8kQUy8nq/5n8IEZ0YeIyBFvdQA8+iFM="
    reference2 = ET.SubElement(signed_info, "ds:Reference")
    reference2.set("URI", "#xadesSignedProperties")
    reference2.set("Type", "http://www.w3.org/2000/09/xmldsig#SignatureProperties")
    digest_method1 = ET.SubElement(reference2, "ds:DigestMethod")
    digest_method1.set("Algorithm", "http://www.w3.org/2001/04/xmlenc#sha256")
    digest_value1 = ET.SubElement(reference2, "ds:DigestValue")
    digest_value1.text = "YjQwZmEyMjM2NDU1YjQwNjM5MTFmYmVkODc4NjM2NTc0N2E3OGFmZjVlMzA1ODAwYWE5Y2ZmYmFjZjRiNjQxNg=="
    signature_value = ET.SubElement(signature, "ds:SignatureValue")
    signature_value.text = "MEQCIDGBRHiPo6yhXIQ9df6pMEkufcGnoqYaS+O8Jn0xagBiAiBtoxpbrwfEJHhUGQHTqzD1ORX5+Z/tumM0wLfZ4cuYRg=="
    key_info = ET.SubElement(signature, "ds:KeyInfo")
    x509_data = ET.SubElement(key_info, "ds:X509Data")
    x509_certificate = ET.SubElement(x509_data, "ds:X509Certificate")
    x509_certificate.text = "MIID6TCCA5CgAwIBAgITbwAAf8tem6jngr16DwABAAB/yzAKBggqhkjOPQQDAjBjMRUwEwYKCZImiZPyLGQBGRYFbG9jYWwxEzARBgoJkiaJk/IsZAEZFgNnb3YxFzAVBgoJkiaJk/IsZAEZFgdleHRnYXp0MRwwGgYDVQQDExNUU1pFSU5WT0lDRS1TdWJDQS0xMB4XDTIyMDkxNDEzMjYwNFoXDTI0MDkxMzEzMjYwNFowTjELMAkGA1UEBhMCU0ExEzARBgNVBAoTCjMxMTExMTExMTExDDAKBgNVBAsTA1RTVDEcMBoGA1UEAxMTVFNULTMxMTExMTExMTEwMTExMzBWMBAGByqGSM49AgEGBSuBBAAKA0IABGGDDKDmhWAITDv7LXqLX2cmr6+qddUkpcLCvWs5rC2O29W/hS4ajAK4Qdnahym6MaijX75Cg3j4aao7ouYXJ9GjggI5MIICNTCBmgYDVR0RBIGSMIGPpIGMMIGJMTswOQYDVQQEDDIxLVRTVHwyLVRTVHwzLWE4NjZiMTQyLWFjOWMtNDI0MS1iZjhlLTdmNzg3YTI2MmNlMjEfMB0GCgmSJomT8ixkAQEMDzMxMTExMTExMTEwMTExMzENMAsGA1UEDAwEMTEwMDEMMAoGA1UEGgwDVFNUMQwwCgYDVQQPDANUU1QwHQYDVR0OBBYEFDuWYlOzWpFN3no1WtyNktQdrA8JMB8GA1UdIwQYMBaAFHZgjPsGoKxnVzWdz5qspyuZNbUvME4GA1UdHwRHMEUwQ6BBoD+GPWh0dHA6Ly90c3RjcmwuemF0Y2EuZ292LnNhL0NlcnRFbnJvbGwvVFNaRUlOVk9JQ0UtU3ViQ0EtMS5jcmwwga0GCCsGAQUFBwEBBIGgMIGdMG4GCCsGAQUFBzABhmJodHRwOi8vdHN0Y3JsLnphdGNhLmdvdi5zYS9DZXJ0RW5yb2xsL1RTWkVpbnZvaWNlU0NBMS5leHRnYXp0Lmdvdi5sb2NhbF9UU1pFSU5WT0lDRS1TdWJDQS0xKDEpLmNydDArBggrBgEFBQcwAYYfaHR0cDovL3RzdGNybC56YXRjYS5nb3Yuc2Evb2NzcDAOBgNVHQ8BAf8EBAMCB4AwHQYDVR0lBBYwFAYIKwYBBQUHAwIGCCsGAQUFBwMDMCcGCSsGAQQBgjcVCgQaMBgwCgYIKwYBBQUHAwIwCgYIKwYBBQUHAwMwCgYIKoZIzj0EAwIDRwAwRAIgOgjNPJW017lsIijmVQVkP7GzFO2KQKd9GHaukLgIWFsCIFJF9uwKhTMxDjWbN+1awsnFI7RLBRxA/6hZ+F1wtaqU"
    signature_object = ET.SubElement(signature, "ds:Object")
    qualifying_properties = ET.SubElement(signature_object, "xades:QualifyingProperties")
    qualifying_properties.set("Target", "signature")
    qualifying_properties.set("xmlns:xades", "http://uri.etsi.org/01903/v1.3.2#")
    signed_properties = ET.SubElement(qualifying_properties, "xades:SignedProperties")
    signed_properties.set("Id", "xadesSignedProperties")
    signed_signature_properties = ET.SubElement(signed_properties, "xades:SignedSignatureProperties")
    signing_time = ET.SubElement(signed_signature_properties, "xades:SigningTime")
    signing_time.text = "2024-01-24T11:36:34Z"
    signing_certificate = ET.SubElement(signed_signature_properties, "xades:SigningCertificate")
    cert = ET.SubElement(signing_certificate, "xades:Cert")
    cert_digest = ET.SubElement(cert, "xades:CertDigest")
    digest_method2 = ET.SubElement(cert_digest, "ds:DigestMethod")
    digest_value2 = ET.SubElement(cert_digest, "ds:DigestValue")
    digest_method2.set("Algorithm", "http://www.w3.org/2001/04/xmlenc#sha256")
    digest_value2.text = "YTJkM2JhYTcwZTBhZTAxOGYwODMyNzY3NTdkZDM3YzhjY2IxOTIyZDZhM2RlZGJiMGY0NDUzZWJhYWI4MDhmYg=="
    issuer_serial = ET.SubElement(cert, "xades:IssuerSerial")
    x509_issuer_name = ET.SubElement(issuer_serial, "ds:X509IssuerName")
    x509_serial_number = ET.SubElement(issuer_serial, "ds:X509SerialNumber")
    x509_issuer_name.text = "CN=TSZEINVOICE-SubCA-1, DC=extgazt, DC=gov, DC=local"
    x509_serial_number.text = "2475382886904809774818644480820936050208702411"
    return invoice


def build_sales_invoice_data(invoice_xml, invoice_data):
    invoice_data = frappe._dict(invoice_data)
    cbc_profile_id = ET.SubElement(invoice_xml, "cbc:ProfileID")
    cbc_profile_id.text = "reporting:1.0"
    cbc_id = ET.SubElement(invoice_xml, "cbc:ID")
    cbc_id.text = str(invoice_data.id)
    cbc_uuid = ET.SubElement(invoice_xml, "cbc:UUID")
    cbc_uuid.text = str(invoice_data.uuid)
    invoice_uuid = cbc_uuid.text
    cbc_issue_date = ET.SubElement(invoice_xml, "cbc:IssueDate")
    cbc_issue_date.text = str(invoice_data.posting_date)
    cbc_issue_time = ET.SubElement(invoice_xml, "cbc:IssueTime")
    cbc_issue_time.text = invoice_data.issue_time
    return invoice_xml, invoice_uuid


def build_invoice_type_code(invoice_xml, invoice_type):
    if invoice_type.lower() == "simplified invoice":  # simplified invoice
        cbc_invoice_type_code = ET.SubElement(invoice_xml, "cbc:InvoiceTypeCode")
        cbc_invoice_type_code.set("name", "0200000")
        cbc_invoice_type_code.text = "388"

    elif invoice_type.lower() == "standard invoice":  # standard invoice
        cbc_invoice_type_code = ET.SubElement(invoice_xml, "cbc:InvoiceTypeCode")
        cbc_invoice_type_code.set("name", "0100000")
        cbc_invoice_type_code.text = "388"

    elif invoice_type.lower() == "simplified credit note":  # simplified Credit note
        cbc_invoice_type_code = ET.SubElement(invoice_xml, "cbc:InvoiceTypeCode")
        cbc_invoice_type_code.set("name", "0200000")
        cbc_invoice_type_code.text = "381"

    elif invoice_type.lower() == "standard credit note":  # Standard Credit note
        cbc_invoice_type_code = ET.SubElement(invoice_xml, "cbc:InvoiceTypeCode")
        cbc_invoice_type_code.set("name", "0100000")
        cbc_invoice_type_code.text = "381"

    elif invoice_type.lower() == "simplified debit note":  # simplified Debit note
        cbc_invoice_type_code = ET.SubElement(invoice_xml, "cbc:InvoiceTypeCode")
        cbc_invoice_type_code.set("name", "0211000")
        cbc_invoice_type_code.text = "383"

    elif invoice_type.lower() == "standard debit note":  # Standard Debit note
        cbc_invoice_type_code = ET.SubElement(invoice_xml, "cbc:InvoiceTypeCode")
        cbc_invoice_type_code.set("name", "0100000")
        cbc_invoice_type_code.text = "383"
    return invoice_xml


def build_doc_reference_compliance(invoice_xml, invoice_data, invoice_type):
    """
    for compliance only
    """
    invoice_data = frappe._dict(invoice_data)
    cbc_document_currency_code = ET.SubElement(invoice_xml, "cbc:DocumentCurrencyCode")
    cbc_document_currency_code.text = invoice_data.currency_code
    cbc_tax_currency_code = ET.SubElement(invoice_xml, "cbc:TaxCurrencyCode")
    cbc_tax_currency_code.text = invoice_data.tax_currency

    if (invoice_type.lower() == "simplified credit note" or invoice_type.lower() == "standard credit note"
            or invoice_type.lower() == "simplified debit note" or invoice_type.lower() == "standard debit note"):
        cac_billing_reference = ET.SubElement(invoice_xml, "cac:BillingReference")
        cac_invoice_document_reference = ET.SubElement(cac_billing_reference, "cac:InvoiceDocumentReference")
        cbc_id_billing = ET.SubElement(cac_invoice_document_reference, "cbc:ID")
        cbc_id_billing.text = invoice_data.return_against if invoice_data.return_against else "666"  # Return against.

    cac_additional_document_reference = ET.SubElement(invoice_xml, "cac:AdditionalDocumentReference")
    cbc_id_counter = ET.SubElement(cac_additional_document_reference, "cbc:ID")
    cbc_id_counter.text = "ICV"
    cbc_uuid_counter = ET.SubElement(cac_additional_document_reference, "cbc:UUID")
    cbc_uuid_counter.text = str(invoice_data.invoice_counter)
    return invoice_xml


def build_additional_references(invoice_xml, invoice_data):
    invoice_data = frappe._dict(invoice_data)
    cac_additional_document_reference2 = ET.SubElement(invoice_xml, "cac:AdditionalDocumentReference")
    cbc_id_pih = ET.SubElement(cac_additional_document_reference2, "cbc:ID")
    cbc_id_pih.text = "PIH"
    cac_attachment_pih = ET.SubElement(cac_additional_document_reference2, "cac:Attachment")
    cbc_embedded_document_binary_object_pih = ET.SubElement(cac_attachment_pih, "cbc:EmbeddedDocumentBinaryObject")
    cbc_embedded_document_binary_object_pih.set("mimeCode", "text/plain")
    cbc_embedded_document_binary_object_pih.text = invoice_data.pih  # Previous invoice hash
    # QR CODE ------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # cac_additional_document_reference_qr = ET.SubElement(invoice_xml, "cac:AdditionalDocumentReference")
    # cbc_id_qr = ET.SubElement(cac_additional_document_reference_qr, "cbc:ID")
    # cbc_id_qr.text = "QR"
    # cac_attachment_qr = ET.SubElement(cac_additional_document_reference_qr, "cac:Attachment")
    # cbc__embedded_document_binary_object_qr = ET.SubElement(cac_attachment_qr, "cbc:EmbeddedDocumentBinaryObject")
    # cbc__embedded_document_binary_object_qr.set("mimeCode", "text/plain")
    # cbc__embedded_document_binary_object_qr.text = ""  # QR code hash value
    # END  QR CODE ------------------------------------------------------------------------------------------------------------------------------------------------------------------
    cac_sign = ET.SubElement(invoice_xml, "cac:Signature")
    cbc_id_sign = ET.SubElement(cac_sign, "cbc:ID")
    cbc_method_sign = ET.SubElement(cac_sign, "cbc:SignatureMethod")
    cbc_id_sign.text = "urn:oasis:names:specification:ubl:signature:Invoice"
    cbc_method_sign.text = "urn:oasis:names:specification:ubl:dsig:enveloped:xades"
    return invoice_xml


def build_seller_data(invoice_xml, seller_details):
    seller_details = frappe._dict(seller_details)
    cac_accounting_supplier_party = ET.SubElement(invoice_xml, "cac:AccountingSupplierParty")
    cac_party = ET.SubElement(cac_accounting_supplier_party, "cac:Party")
    # TODO: Dummy data until looping into party identifications for the seller.
    cac_party_identification = ET.SubElement(cac_party, "cac:PartyIdentification")
    cbc_id_supplier = ET.SubElement(cac_party_identification, "cbc:ID")
    cbc_id_supplier.set("schemeID", "CRN")
    cbc_id_supplier.text = "12344444"

    cac_postal_address = ET.SubElement(cac_party, "cac:PostalAddress")
    cbc_street_name = ET.SubElement(cac_postal_address, "cbc:StreetName")
    cbc_street_name.text = seller_details.street_name
    cbc_building_number = ET.SubElement(cac_postal_address, "cbc:BuildingNumber")
    cbc_building_number.text = seller_details.building_number
    cbc_plot_identification = ET.SubElement(cac_postal_address, "cbc:PlotIdentification")
    cbc_plot_identification.text = seller_details.plot_identification
    cbc_city_subdivision_name = ET.SubElement(cac_postal_address, "cbc:CitySubdivisionName")
    cbc_city_subdivision_name.text = seller_details.city_subdivision_name
    cbc_city_name = ET.SubElement(cac_postal_address, "cbc:CityName")
    cbc_city_name.text = seller_details.city_name
    cbc_postal_zone = ET.SubElement(cac_postal_address, "cbc:PostalZone")
    cbc_postal_zone.text = seller_details.postal_zone
    cbc_country_subentity = ET.SubElement(cac_postal_address, "cbc:CountrySubentity")
    cbc_country_subentity.text = seller_details.CountrySubentity

    cac_country = ET.SubElement(cac_postal_address, "cac:Country")
    cbc_identification_code = ET.SubElement(cac_country, "cbc:IdentificationCode")
    cbc_identification_code.text = seller_details.country_code
    cac_party_tax_scheme = ET.SubElement(cac_party, "cac:PartyTaxScheme")
    cbc_company_id = ET.SubElement(cac_party_tax_scheme, "cbc:CompanyID")
    cbc_company_id.text = seller_details.company_id
    cac_tax_scheme = ET.SubElement(cac_party_tax_scheme, "cac:TaxScheme")
    cbc_id_tax_scheme = ET.SubElement(cac_tax_scheme, "cbc:ID")
    cbc_id_tax_scheme.text = "VAT"
    cac_party_legal_entity = ET.SubElement(cac_party, "cac:PartyLegalEntity")
    cbc_registration_name = ET.SubElement(cac_party_legal_entity, "cbc:RegistrationName")
    cbc_registration_name.text = seller_details.seller_name
    return invoice_xml


def build_customer_data(invoice_xml, customer_details):
    customer_details = frappe._dict(customer_details)
    cac_accounting_customer_party = ET.SubElement(invoice_xml, "cac:AccountingCustomerParty")
    cac_party = ET.SubElement(cac_accounting_customer_party, "cac:Party")
    if customer_details.PartyIdentification:
        # TODO: Dummy data until looping into party identifications for the customer.
        cac_party_identification = ET.SubElement(cac_party, "cac:PartyIdentification")
        cbc_id_customer = ET.SubElement(cac_party_identification, "cbc:ID")
        cbc_id_customer.set("schemeID", "CRN")
        cbc_id_customer.text = "1231313123123"

    cac_postal_address = ET.SubElement(cac_party, "cac:PostalAddress")
    cbc_street_name = ET.SubElement(cac_postal_address, "cbc:StreetName")
    cbc_street_name.text = customer_details.sreet_name
    cbc_building_number = ET.SubElement(cac_postal_address, "cbc:BuildingNumber")
    cbc_building_number.text = customer_details.building_number
    cbc_plot_identification = ET.SubElement(cac_postal_address, "cbc:PlotIdentification")
    cbc_plot_identification.text = customer_details.plot_identification

    cbc_city_subdivision_name = ET.SubElement(cac_postal_address, "cbc:CitySubdivisionName")
    cbc_city_subdivision_name.text = customer_details.city_subdivision_name
    cbc_city_name = ET.SubElement(cac_postal_address, "cbc:CityName")
    cbc_city_name.text = customer_details.city_name
    cbc_postal_zone = ET.SubElement(cac_postal_address, "cbc:PostalZone")
    cbc_postal_zone.text = customer_details.postal_zone
    cbc_country_subentity = ET.SubElement(cac_postal_address, "cbc:CountrySubentity")
    cbc_country_subentity.text = customer_details.CountrySubentity
    cac_country = ET.SubElement(cac_postal_address, "cac:Country")
    cbc_identification_code = ET.SubElement(cac_country, "cbc:IdentificationCode")
    cbc_identification_code.text = customer_details.identification_code
    cac_party_tax_scheme = ET.SubElement(cac_party, "cac:PartyTaxScheme")
    cac_tax_scheme = ET.SubElement(cac_party_tax_scheme, "cac:TaxScheme")
    cbc_id_tax_scheme = ET.SubElement(cac_tax_scheme, "cbc:ID")
    cbc_id_tax_scheme.text = "VAT"
    cac_party_legal_entity = ET.SubElement(cac_party, "cac:PartyLegalEntity")
    cbc_registration_name = ET.SubElement(cac_party_legal_entity, "cbc:RegistrationName")
    cbc_registration_name.text = customer_details.registration_name
    return invoice_xml


def build_delivery_And_payment_means(invoice_xml, invoice_data):
    invoice_data = frappe._dict(invoice_data)
    cac_delivery = ET.SubElement(invoice_xml, "cac:Delivery")
    cbc_actual_delivery_date = ET.SubElement(cac_delivery, "cbc:ActualDeliveryDate")
    cbc_actual_delivery_date.text = str(invoice_data.due_date) or str(now_datetime())
    cac_payment_means = ET.SubElement(invoice_xml, "cac:PaymentMeans")
    cbc_payment_means_code = ET.SubElement(cac_payment_means, "cbc:PaymentMeansCode")
    cbc_payment_means_code.text = "32"

    if invoice_data.is_return == 1:
        cbc_instruction_note = ET.SubElement(cac_payment_means, "cbc:InstructionNote")
        cbc_instruction_note.text = "Cancellation"
    return invoice_xml


def build_delivery_and_payment_means_for_compliance(invoice_xml, invoice_data, invoice_type):
    """
    For Compliance only
    """
    invoice_data = frappe._dict(invoice_data)
    cac_delivery = ET.SubElement(invoice_xml, "cac:Delivery")
    cbc_actual_delivery_date = ET.SubElement(cac_delivery, "cbc:ActualDeliveryDate")
    cbc_actual_delivery_date.text = str(invoice_data.due_date) or str(now_datetime())
    cac_payment_means = ET.SubElement(invoice_xml, "cac:PaymentMeans")
    cbc_payment_means_code = ET.SubElement(cac_payment_means, "cbc:PaymentMeansCode")
    cbc_payment_means_code.text = "32"
    if (invoice_type.lower() == "simplified credit note" or invoice_type.lower() == "standard credit note"
            or invoice_type.lower() == "simplified debit note" or invoice_type.lower() == "standard debit note"):
        cbc_instruction_note = ET.SubElement(cac_payment_means, "cbc:InstructionNote")
        cbc_instruction_note.text = "Cancellation"
    return invoice_xml


def build_tax_data(invoice_xml, invoice_data):
    invoice_data = frappe._dict(invoice_data)
    sales_invoice_doc = frappe.get_doc("Sales Invoice", invoice_data.id)
    # for foreign currency
    if invoice_data.currency_code != "SAR":
        cac_tax_total = ET.SubElement(invoice_xml, "cac:TaxTotal")
        cbc_tax_amount_sar = ET.SubElement(cac_tax_total, "cbc:TaxAmount")
        cbc_tax_amount_sar.set("currencyID", "SAR")  # SAR is as zatca requires tax amount in SAR
        tax_amount_without_retention_sar = flt(
            (sales_invoice_doc.conversion_rate or 18.00) * abs(get_tax_total_from_items(sales_invoice_doc)), 2)
        cbc_tax_amount_sar.text = str(
            flt(tax_amount_without_retention_sar, 2))  # str( abs(sales_invoice_doc.base_total_taxes_and_charges))
    # end for foreign currency

    # for SAR currency
    if invoice_data.currency_code == "SAR":
        cac_tax_total = ET.SubElement(invoice_xml, "cac:TaxTotal")
        cbc_tax_amount_sar = ET.SubElement(cac_tax_total, "cbc:TaxAmount")
        cbc_tax_amount_sar.set("currencyID", "SAR")  # SAR is as zatca requires tax amount in SAR
        tax_amount_without_retention_sar = flt(abs(get_tax_total_from_items(sales_invoice_doc)), 2)
        cbc_tax_amount_sar.text = str(
            flt(tax_amount_without_retention_sar, 2))  # str( abs(sales_invoice_doc.base_total_taxes_and_charges))
    # end for SAR currency

    cac_tax_total = ET.SubElement(invoice_xml, "cac:TaxTotal")
    cbc_tax_amount = ET.SubElement(cac_tax_total, "cbc:TaxAmount")
    cbc_tax_amount.set("currencyID", invoice_data.tax_currency)  # SAR is as zatca requires tax amount in SAR
    tax_amount_without_retention = flt(abs(get_tax_total_from_items(sales_invoice_doc)), 2)
    cbc_tax_amount.text = str(
        flt(tax_amount_without_retention, 2))  # str( abs(sales_invoice_doc.base_total_taxes_and_charges))
    cac_tax_subtotal = ET.SubElement(cac_tax_total, "cac:TaxSubtotal")
    cbc_taxable_amount = ET.SubElement(cac_tax_subtotal, "cbc:TaxableAmount")
    cbc_taxable_amount.set("currencyID", invoice_data.currency_code)
    cbc_taxable_amount.text = str(abs(flt(invoice_data.total, 2)))

    cac_tax_category = ET.SubElement(cac_tax_subtotal, "cac:TaxCategory")
    cbc_id_cat = ET.SubElement(cac_tax_category, "cbc:ID")
    cbc_id_cat.text = "S"
    cbc_percent_cat = ET.SubElement(cac_tax_category, "cbc:Percent")
    cbc_percent_cat.text = str(flt(sales_invoice_doc.taxes[0].rate, 2))
    cac_tax_scheme = ET.SubElement(cac_tax_category, "cac:TaxScheme")
    cbc_id_scheme = ET.SubElement(cac_tax_scheme, "cbc:ID")
    cbc_id_scheme.text = "VAT"

    cac_legal_monetary_total = ET.SubElement(invoice_xml, "cac:LegalMonetaryTotal")
    cbc_line_extension_amount = ET.SubElement(cac_legal_monetary_total, "cbc:LineExtensionAmount")
    cbc_line_extension_amount.set("currencyID", invoice_data.currency_code)
    cbc_line_extension_amount.text = str(abs(invoice_data.net_total))
    cbc_tax_exclusive_amount = ET.SubElement(cac_legal_monetary_total, "cbc:TaxExclusiveAmount")
    cbc_tax_exclusive_amount.set("currencyID", invoice_data.currency_code)
    cbc_tax_exclusive_amount.text = str(abs(invoice_data.net_total))
    cbc_tax_inclusive_amount = ET.SubElement(cac_legal_monetary_total, "cbc:TaxInclusiveAmount")
    cbc_tax_inclusive_amount.set("currencyID", invoice_data.currency_code)
    cbc_tax_inclusive_amount.text = str(flt(abs(invoice_data.net_total) + abs(tax_amount_without_retention), 2))
    cbc_allowance_total_amount = ET.SubElement(cac_legal_monetary_total, "cbc:AllowanceTotalAmount")
    cbc_allowance_total_amount.set("currencyID", invoice_data.currency_code)
    cbc_allowance_total_amount.text = str(invoice_data.amount)
    cbc_payable_amount = ET.SubElement(cac_legal_monetary_total, "cbc:PayableAmount")
    cbc_payable_amount.set("currencyID", invoice_data.currency_code)
    cbc_payable_amount.text = str(flt(abs(invoice_data.net_total) + abs(tax_amount_without_retention), 2))
    return invoice_xml


def build_item_data(invoice_xml, invoice_data):
    invoice_data = frappe._dict(invoice_data)
    sales_invoice_doc = frappe.get_doc("Sales Invoice", invoice_data.id)
    for item in sales_invoice_doc.items:
        item_tax_amount, item_tax_percentage = get_tax_for_item(sales_invoice_doc.taxes[0].item_wise_tax_detail,
                                                                item.item_code)
        cac_invoice_line = ET.SubElement(invoice_xml, "cac:InvoiceLine")
        cbc_id_item = ET.SubElement(cac_invoice_line, "cbc:ID")
        cbc_id_item.text = str(item.idx)
        cbc_invoiced_quantity = ET.SubElement(cac_invoice_line, "cbc:InvoicedQuantity")
        cbc_invoiced_quantity.set("unitCode", str(item.uom))
        cbc_invoiced_quantity.text = str(abs(item.qty))
        cbc_line_extension_amount = ET.SubElement(cac_invoice_line, "cbc:LineExtensionAmount")
        cbc_line_extension_amount.set("currencyID", invoice_data.currency_code)
        cbc_line_extension_amount.text = str(abs(item.amount))
        cac_tax_total = ET.SubElement(cac_invoice_line, "cac:TaxTotal")
        cbc_tax_amount = ET.SubElement(cac_tax_total, "cbc:TaxAmount")
        cbc_tax_amount.set("currencyID", invoice_data.tax_currency)
        cbc_tax_amount.text = str(abs(flt(item_tax_percentage * item.amount / 100, 2)))
        cbc_rounding_amount = ET.SubElement(cac_tax_total, "cbc:RoundingAmount")
        cbc_rounding_amount.set("currencyID", invoice_data.tax_currency)
        cbc_rounding_amount.text = str(abs(flt(item.amount + (item_tax_percentage * item.amount / 100), 2)))
        cac_item = ET.SubElement(cac_invoice_line, "cac:Item")
        cbc_name = ET.SubElement(cac_item, "cbc:Name")
        cbc_name.text = item.item_code
        cac_classified_tax_category = ET.SubElement(cac_item, "cac:ClassifiedTaxCategory")
        cbc_id_tax_cat = ET.SubElement(cac_classified_tax_category, "cbc:ID")
        cbc_id_tax_cat.text = "S"
        cbc_percent_tax = ET.SubElement(cac_classified_tax_category, "cbc:Percent")
        cbc_percent_tax.text = str(flt(item_tax_percentage, 2))
        cac_tax_scheme = ET.SubElement(cac_classified_tax_category, "cac:TaxScheme")
        cbc_id_tax_scheme = ET.SubElement(cac_tax_scheme, "cbc:ID")
        cbc_id_tax_scheme.text = "VAT"
        cac_price = ET.SubElement(cac_invoice_line, "cac:Price")
        cbc_price_amount = ET.SubElement(cac_price, "cbc:PriceAmount")
        cbc_price_amount.set("currencyID", invoice_data.currency_code)
        cbc_price_amount.text = str(abs(item.net_rate))

    return invoice_xml
