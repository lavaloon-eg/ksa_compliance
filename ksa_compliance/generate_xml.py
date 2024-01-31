import base64
import hashlib
import os
import sys
import re

import OpenSSL
import chilkat2
import requests
from path import Path
from subprocess import call

import frappe
import json
from frappe.utils.logger import get_logger


@frappe.whitelist(allow_guest=True)
def generate_xml(input_data: dict = None):
    """
    For postman testing purpose
    """
    data = input_data or frappe.request.data
    if not isinstance(data, dict):
        data = json.loads(data)

    invoice_type = data.get("invoice_type")
    template = "simplified_e_invoice.xml" if invoice_type.lower() == "simplified" else "standard_e_invoice.xml"

    # render XML Template
    invoice_xml = frappe.render_template(
        f"ksa_compliance/templates/{template}",
        context={"invoice": data.get("invoice"), "seller": data.get("seller"), "buyer": data.get("buyer"),
                 "business_settings": data.get("business_settings")},
        is_path=True
    )
    invoice_xml = invoice_xml.replace("&", "&amp;")
    invoice_xml = invoice_xml.replace("\n", "")

    return invoice_xml


def generate_xml_file(data, invoice_type: str = "Simplified"):
    """
    For Generating cycle
    """

    template = "simplified_e_invoice.xml" if invoice_type.lower() == "simplified" else "standard_e_invoice.xml"

    # render XML Template
    invoice_xml = frappe.render_template(
        f"ksa_compliance/templates/{template}",
        context={
            "invoice": data.get("invoice"),
            "seller_details": data.get("seller_details"),
            "buyer_details": data.get("buyer_details"),
            "business_settings": data.get("business_settings")},
        is_path=True
    )
    invoice_xml = invoice_xml.replace("&", "&amp;")
    invoice_xml = invoice_xml.replace("\n", "")
    xml_filename = generate_einvoice_xml_fielname(data['business_settings'], data["invoice"])
    file = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": xml_filename,
            "attached_to_doctype": "Sales Invoice",
            "attached_to_name": data["invoice"]["id"],
            "content": invoice_xml,
        }
    )
    file.insert()
    invoice_hash = hashing_invoice(data["invoice"]["id"])
    # digital_signature = generate_digital_signature(invoice_hash)  # TODO: Need investigation to implement
    encoded_hashed_certificate = generate_hashing_certificate()
    # generate_sign(file.file_url, invoice_hash, encoded_hashed_certificate)


def generate_einvoice_xml_fielname(business_settings, invoice):
    vat_registration_number = business_settings["company_id"]
    invoice_date = invoice["issue_date"].replace("-", "")
    invoice_time = invoice["issue_time"].replace(":", "")
    invoice_number = invoice["id"]
    file_name = vat_registration_number + "_" + invoice_date + "T" + invoice_time + "_" + invoice_number
    progressive_name = frappe.model.naming.make_autoname(file_name)
    progressive_name = progressive_name[:len(file_name)]
    return progressive_name + ".xml"


@frappe.whitelist(allow_guest=True)
def generate_csr(business_settings_id):
    logger = get_logger("csr-generation")
    try:
        settings = frappe.get_doc('ZATCA Business Settings', business_settings_id)
        csr_config_file = 'csrconfig.txt'
        privatekey_file = "privatekey.pem"
        pubkey_file = "pubkey.pem"
        cwd = os.getcwd()
        site = frappe.local.site

        Path(f"{cwd}/{site}/private/files").chdir()

        try:
            cmd = f"openssl ecparam -name secp256k1 -genkey -noout -out {privatekey_file}"
            decrypted1 = call(cmd, shell=True)  # execute command with the shell

            cmd1 = f"openssl ec -in {privatekey_file} -pubout -conv_form compressed -out {pubkey_file}"
            decrypted2 = call(cmd1, shell=True)

            cmd2 = f"openssl req -new -sha256 -key {privatekey_file} -extensions v3_req -config {csr_config_file} -out taxpayer.csr"
            decrypted3 = call(cmd2, shell=True)

            cmd3 = "openssl base64 -in taxpayer.csr -out taxpayerCSRbase64Encoded.txt"
            decrypted4 = call(cmd3, shell=True)

        except Exception as e:
            frappe.throw("An error occurred: " + str(e))
    except Exception as e:
        frappe.throw("error occurred in generate csr" + str(e))


@frappe.whitelist(allow_guest=True)
def create_CSID(business_settings_id):
    try:
        settings = frappe.get_doc("ZATCA Business Settings", business_settings_id)
        cwd = os.getcwd()
        site = frappe.local.site

        Path(f"{cwd}/{site}/private/files").chdir()

        with open(r'taxpayerCSRbase64Encoded.txt', 'r') as file:
            data = file.read()
            data = data.replace("\n", "")
            data = data.replace("\r", "")
        with open(r'taxpayerCSRbase64Encoded3.txt', 'w') as file:
            file.write(data)

        payload = json.dumps({
            "csr": data
        })
        headers = {
            'accept': 'application/json',
            'OTP': settings.otp,
            'Accept-Version': 'V2',
            'Content-Type': 'application/json'
        }
        url = 'https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal/compliance'

        response = requests.post(url=url, headers=headers, data=payload)
        # response.status_code = 400
        if response.status_code == 400:
            frappe.throw("Error: " + "OTP is not valid", response.text)
        if response.status_code != 200:
            frappe.throw("Error: " + "Error in Certificate or OTP: " + "<br> <br>" + response.text)

        data = json.loads(response.text)
        concatenated_value = data["binarySecurityToken"] + ":" + data["secret"]
        encoded_value = base64.b64encode(concatenated_value.encode()).decode()

        with open(f"cert.pem", 'w') as file:  # attaching X509 certificate
            file.write(base64.b64decode(data["binarySecurityToken"]).decode('utf-8'))

        settings.set("basic_auth", encoded_value)
        settings.save(ignore_permissions=True)
        settings.set("compliance_request_id", data["requestID"])
        settings.save(ignore_permissions=True)
    except Exception as e:
        frappe.throw("error in csid formation: " + str(e))


def get_latest_generated_csr_file(folder_path='.'):
    try:
        files = [f for f in os.listdir(folder_path) if
                 f.startswith("generated-csr") and os.path.isfile(os.path.join(folder_path, f))]
        if not files:
            return None
        latest_file = files[0]
        print(latest_file)
        return os.path.join(folder_path, latest_file)
    except Exception as e:
        frappe.throw(" error in get_latest_generated_csr_file: " + str(e))


def generate_sign(invoice_id, file_url):
    import xml.etree.ElementTree as ET

    signed_xml_file_name = "signedXml.xml"
    cwd = os.getcwd()
    site = frappe.local.site

    file_url = f"{cwd}/{site}/public/{file_url}"
    tree = ET.parse(file_url)
    root = tree.getroot()
    # Start UBL STATIC DATA
    ubl_extensions = ET.SubElement(root, "ext:UBLExtensions")
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
    id = ET.SubElement(signature_information, "cbc:ID")
    id.text = "urn:oasis:names:specification:ubl:signature:1"
    referenced_signatureID = ET.SubElement(signature_information, "sbc:ReferencedSignatureID")
    referenced_signatureID.text = "urn:oasis:names:specification:ubl:signature:Invoice"
    signature = ET.SubElement(signature_information, "ds:Signature")
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
    XPath = ET.SubElement(transform, "ds:XPath")
    XPath.text = "not(//ancestor-or-self::ext:UBLExtensions)"
    transform2 = ET.SubElement(transforms, "ds:Transform")
    transform2.set("Algorithm", "http://www.w3.org/TR/1999/REC-xpath-19991116")
    XPath2 = ET.SubElement(transform2, "ds:XPath")
    XPath2.text = "not(//ancestor-or-self::cac:Signature)"
    Transform3 = ET.SubElement(transforms, "ds:Transform")
    Transform3.set("Algorithm", "http://www.w3.org/TR/1999/REC-xpath-19991116")
    XPath3 = ET.SubElement(Transform3, "ds:XPath")
    XPath3.text = "not(//ancestor-or-self::cac:AdditionalDocumentReference[cbc:ID='QR'])"
    Transform4 = ET.SubElement(transforms, "ds:Transform")
    Transform4.set("Algorithm", "http://www.w3.org/2006/12/xml-c14n11")
    Diges_Method = ET.SubElement(reference, "ds:DigestMethod")
    Diges_Method.set("Algorithm", "http://www.w3.org/2001/04/xmlenc#sha256")
    Diges_value = ET.SubElement(reference, "ds:DigestValue")
    Diges_value.text = "O/vEnAxjLAlw8kQUy8nq/5n8IEZ0YeIyBFvdQA8+iFM="
    Reference2 = ET.SubElement(signed_info, "ds:Reference")
    Reference2.set("URI", "#xadesSignedProperties")
    Reference2.set("Type", "http://www.w3.org/2000/09/xmldsig#SignatureProperties")
    Digest_Method1 = ET.SubElement(Reference2, "ds:DigestMethod")
    Digest_Method1.set("Algorithm", "http://www.w3.org/2001/04/xmlenc#sha256")
    Digest_value1 = ET.SubElement(Reference2, "ds:DigestValue")
    Digest_value1.text = "YjQwZmEyMjM2NDU1YjQwNjM5MTFmYmVkODc4NjM2NTc0N2E3OGFmZjVlMzA1ODAwYWE5Y2ZmYmFjZjRiNjQxNg=="
    Signature_Value = ET.SubElement(signature, "ds:SignatureValue")
    Signature_Value.text = "MEQCIDGBRHiPo6yhXIQ9df6pMEkufcGnoqYaS+O8Jn0xagBiAiBtoxpbrwfEJHhUGQHTqzD1ORX5+Z/tumM0wLfZ4cuYRg=="
    KeyInfo = ET.SubElement(signature, "ds:KeyInfo")
    X509Data = ET.SubElement(KeyInfo, "ds:X509Data")
    X509Certificate = ET.SubElement(X509Data, "ds:X509Certificate")
    # Cert.pem
    X509Certificate.text = "MIID6TCCA5CgAwIBAgITbwAAf8tem6jngr16DwABAAB/yzAKBggqhkjOPQQDAjBjMRUwEwYKCZImiZPyLGQBGRYFbG9jYWwxEzARBgoJkiaJk/IsZAEZFgNnb3YxFzAVBgoJkiaJk/IsZAEZFgdleHRnYXp0MRwwGgYDVQQDExNUU1pFSU5WT0lDRS1TdWJDQS0xMB4XDTIyMDkxNDEzMjYwNFoXDTI0MDkxMzEzMjYwNFowTjELMAkGA1UEBhMCU0ExEzARBgNVBAoTCjMxMTExMTExMTExDDAKBgNVBAsTA1RTVDEcMBoGA1UEAxMTVFNULTMxMTExMTExMTEwMTExMzBWMBAGByqGSM49AgEGBSuBBAAKA0IABGGDDKDmhWAITDv7LXqLX2cmr6+qddUkpcLCvWs5rC2O29W/hS4ajAK4Qdnahym6MaijX75Cg3j4aao7ouYXJ9GjggI5MIICNTCBmgYDVR0RBIGSMIGPpIGMMIGJMTswOQYDVQQEDDIxLVRTVHwyLVRTVHwzLWE4NjZiMTQyLWFjOWMtNDI0MS1iZjhlLTdmNzg3YTI2MmNlMjEfMB0GCgmSJomT8ixkAQEMDzMxMTExMTExMTEwMTExMzENMAsGA1UEDAwEMTEwMDEMMAoGA1UEGgwDVFNUMQwwCgYDVQQPDANUU1QwHQYDVR0OBBYEFDuWYlOzWpFN3no1WtyNktQdrA8JMB8GA1UdIwQYMBaAFHZgjPsGoKxnVzWdz5qspyuZNbUvME4GA1UdHwRHMEUwQ6BBoD+GPWh0dHA6Ly90c3RjcmwuemF0Y2EuZ292LnNhL0NlcnRFbnJvbGwvVFNaRUlOVk9JQ0UtU3ViQ0EtMS5jcmwwga0GCCsGAQUFBwEBBIGgMIGdMG4GCCsGAQUFBzABhmJodHRwOi8vdHN0Y3JsLnphdGNhLmdvdi5zYS9DZXJ0RW5yb2xsL1RTWkVpbnZvaWNlU0NBMS5leHRnYXp0Lmdvdi5sb2NhbF9UU1pFSU5WT0lDRS1TdWJDQS0xKDEpLmNydDArBggrBgEFBQcwAYYfaHR0cDovL3RzdGNybC56YXRjYS5nb3Yuc2Evb2NzcDAOBgNVHQ8BAf8EBAMCB4AwHQYDVR0lBBYwFAYIKwYBBQUHAwIGCCsGAQUFBwMDMCcGCSsGAQQBgjcVCgQaMBgwCgYIKwYBBQUHAwIwCgYIKwYBBQUHAwMwCgYIKoZIzj0EAwIDRwAwRAIgOgjNPJW017lsIijmVQVkP7GzFO2KQKd9GHaukLgIWFsCIFJF9uwKhTMxDjWbN+1awsnFI7RLBRxA/6hZ+F1wtaqU"
    Object = ET.SubElement(signature, "ds:Object")
    QualifyingProperties = ET.SubElement(Object, "xades:QualifyingProperties")
    QualifyingProperties.set("Target", "signature")
    QualifyingProperties.set("xmlns:xades", "http://uri.etsi.org/01903/v1.3.2#")
    SignedProperties = ET.SubElement(QualifyingProperties, "xades:SignedProperties")
    SignedProperties.set("Id", "xadesSignedProperties")
    SignedSignatureProperties = ET.SubElement(SignedProperties, "xades:SignedSignatureProperties")
    SigningTime = ET.SubElement(SignedSignatureProperties, "xades:SigningTime")
    SigningTime.text = "2024-01-24T11:36:34Z"
    SigningCertificate = ET.SubElement(SignedSignatureProperties, "xades:SigningCertificate")
    Cert = ET.SubElement(SigningCertificate, "xades:Cert")
    CertDigest = ET.SubElement(Cert, "xades:CertDigest")
    Digest_Method2 = ET.SubElement(CertDigest, "ds:DigestMethod")
    Digest_Value2 = ET.SubElement(CertDigest, "ds:DigestValue")
    Digest_Method2.set("Algorithm", "http://www.w3.org/2001/04/xmlenc#sha256")
    Digest_Value2.text = "YTJkM2JhYTcwZTBhZTAxOGYwODMyNzY3NTdkZDM3YzhjY2IxOTIyZDZhM2RlZGJiMGY0NDUzZWJhYWI4MDhmYg=="
    IssuerSerial = ET.SubElement(Cert, "xades:IssuerSerial")
    X509IssuerName = ET.SubElement(IssuerSerial, "ds:X509IssuerName")
    X509SerialNumber = ET.SubElement(IssuerSerial, "ds:X509SerialNumber")
    X509IssuerName.text = "CN=TSZEINVOICE-SubCA-1, DC=extgazt, DC=gov, DC=local"
    X509SerialNumber.text = "2475382886904809774818644480820936050208702411"

    tree.write('output.xml')
    return

    cwd = os.getcwd()

    attachments = frappe.get_all(
        "File",
        fields=("name", "file_name", "attached_to_name", "file_url"),
        filters={"attached_to_name": ("in", invoice_id), "attached_to_doctype": "Sales Invoice"},
    )

    for attachment in attachments:
        if (
                attachment.file_name
                and attachment.file_name.endswith(".xml")

        ):
            xml_filename = attachment.file_name
            file_url = attachment.file_url

    cwd = os.getcwd()
    signedxmlll = "Signed" + xml_filename
    site = (frappe.local.site)
    # xml_file = cwd+'/mum128.erpgulf.com/public'+file_url
    xml_file = cwd + '/' + site + '/public' + file_url

    sbXml = chilkat2.StringBuilder()
    success = sbXml.LoadFile(xml_file, "utf-8")

    if (success == False):
        print("Failed to load XML file to be signed.")
        sys.exit()

    gen = chilkat2.XmlDSigGen()

    gen.SigLocation = "Invoice|ext:UBLExtensions|ext:UBLExtension|ext:ExtensionContent|sig:UBLDocumentSignatures|sac:SignatureInformation"

    gen.SigLocationMod = 0
    gen.SigId = "signature"
    gen.SigNamespacePrefix = "ds"
    gen.SigNamespaceUri = "http://www.w3.org/2000/09/xmldsig#"
    gen.SignedInfoCanonAlg = "C14N_11"
    gen.SignedInfoDigestMethod = "sha256"

    # Create an Object to be added to the Signature.
    object1 = chilkat2.Xml()
    object1.Tag = "xades:QualifyingProperties"
    object1.AddAttribute("xmlns:xades", "http://uri.etsi.org/01903/v1.3.2#")
    object1.AddAttribute("Target", "signature")
    object1.UpdateAttrAt("xades:SignedProperties", True, "Id", "xadesSignedProperties")
    object1.UpdateChildContent("xades:SignedProperties|xades:SignedSignatureProperties|xades:SigningTime",
                               "TO BE GENERATED BY CHILKAT")
    object1.UpdateAttrAt(
        "xades:SignedProperties|xades:SignedSignatureProperties|xades:SigningCertificate|xades:Cert|xades:CertDigest|ds:DigestMethod",
        True, "Algorithm", "http://www.w3.org/2001/04/xmlenc#sha256")
    object1.UpdateChildContent(
        "xades:SignedProperties|xades:SignedSignatureProperties|xades:SigningCertificate|xades:Cert|xades:CertDigest|ds:DigestValue",
        "TO BE GENERATED BY CHILKAT")
    object1.UpdateChildContent(
        "xades:SignedProperties|xades:SignedSignatureProperties|xades:SigningCertificate|xades:Cert|xades:IssuerSerial|ds:X509IssuerName",
        "TO BE GENERATED BY CHILKAT")
    object1.UpdateChildContent(
        "xades:SignedProperties|xades:SignedSignatureProperties|xades:SigningCertificate|xades:Cert|xades:IssuerSerial|ds:X509SerialNumber",
        "TO BE GENERATED BY CHILKAT")

    gen.AddObject("", object1.GetXml(), "", "")

    xml1 = chilkat2.Xml()
    xml1.Tag = "ds:Transforms"
    xml1.UpdateAttrAt("ds:Transform", True, "Algorithm", "http://www.w3.org/TR/1999/REC-xpath-19991116")
    xml1.UpdateChildContent("ds:Transform|ds:XPath", "not(//ancestor-or-self::ext:UBLExtensions)")
    xml1.UpdateAttrAt("ds:Transform[1]", True, "Algorithm", "http://www.w3.org/TR/1999/REC-xpath-19991116")
    xml1.UpdateChildContent("ds:Transform[1]|ds:XPath", "not(//ancestor-or-self::cac:Signature)")
    xml1.UpdateAttrAt("ds:Transform[2]", True, "Algorithm", "http://www.w3.org/TR/1999/REC-xpath-19991116")
    xml1.UpdateChildContent("ds:Transform[2]|ds:XPath",
                            "not(//ancestor-or-self::cac:AdditionalDocumentReference[cbc:ID='QR'])")
    xml1.UpdateAttrAt("ds:Transform[3]", True, "Algorithm", "http://www.w3.org/2006/12/xml-c14n11")

    gen.AddSameDocRef2("", "sha256", xml1, "")

    gen.SetRefIdAttr("", "invoiceSignedData")

    gen.AddObjectRef("xadesSignedProperties", "sha256", "", "", "http://www.w3.org/2000/09/xmldsig#SignatureProperties")
    cwd = os.getcwd()

    # new_path = "/salama/salama/einvoice-bench/apps/ksa_compliance/ksa_compliance"
    cer = cwd + '/taxpayer.csr'
    pkey = cwd + '/privatekey.pem'
    pfx = cwd + '/pf.pfx'
    key = OpenSSL.crypto.PKey()
    key.generate_key(OpenSSL.crypto.TYPE_RSA, 1024)
    cert = OpenSSL.crypto.X509()
    cert.set_serial_number(0)
    cert.get_subject().CN = "me"
    cert.set_issuer(cert.get_subject())
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)
    cert.set_pubkey(key)
    cert.sign(key, 'md5')
    open(cer, 'wb').write(
        OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, cert))
    open(pkey, 'wb').write(
        OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, key))
    p12 = OpenSSL.crypto.PKCS12()
    p12.set_privatekey(key)
    p12.set_certificate(cert)
    open(pfx, 'wb').write(p12.export())
    # Provide a certificate + private key. (PFX password is test123)
    certFromPfx = chilkat2.Cert()

    success = certFromPfx.LoadPfxFile(pfx, "")

    if (success != True):
        print(certFromPfx.LastErrorText)
        sys.exit()

    # Alternatively, if your certificate and private key are in separate PEM files, do this:
    certt = chilkat2.Cert()
    success = certt.LoadFromFile(cer)

    if (success != True):
        return (cert.LastErrorText)
        sys.exit()

    # return (cert.SubjectCN)

    # Load the private key.
    privKey = chilkat2.PrivateKey()
    success = privKey.LoadPemFile(pkey)

    if (success != True):
        print(privKey.LastErrorText)
        sys.exit()

    print("Key Type: " + privKey.KeyType)

    # Associate the private key with the certificate.
    success = certt.SetPrivateKey(privKey)

    if (success != True):
        print(certt.LastErrorText)
        sys.exit()

    # The certificate passed to SetX509Cert must have an associated private key.
    # If the cert was loaded from a PFX, then it should automatically has an associated private key.
    # If the cert was loaded from PEM, then the private key was explicitly associated as shown above.
    success = gen.SetX509Cert(certt, True)

    if (success != True):
        print(gen.LastErrorText)
        sys.exit()

    gen.KeyInfoType = "X509Data"

    gen.X509Type = "Certificate"

    # Starting in Chilkat v9.5.0.92, add the "ZATCA" behavior to produce the format required by ZATCA.
    gen.Behaviors = "IndentedSignature,TransformSignatureXPath,ZATCA"

    # Sign the XML...
    success = gen.CreateXmlDSigSb(sbXml)

    if (success != True):
        print(gen.LastErrorText)
        sys.exit()

    # Save the signed XML to a file.
    # success = sbXml.WriteFile(cwd+'/mum128.erpgulf.com'+"/public/files/"+ signedxmlll,"utf-8",False)
    success = sbXml.WriteFile(cwd + '/' + site + "/public/files/" + signedxmlll, "utf-8", False)

    print(sbXml.GetAsString())

    signedd_xml = sbXml.GetAsString()

    # Verify the signatures produced
    verifier = chilkat2.XmlDSig()
    success = verifier.LoadSignatureSb(sbXml)
    if (success != True):
        print(verifier.LastErrorText)
        sys.exit()

    # to validate signed XML according to ZATCA needs.

    verifier.UncommonOptions = "ZATCA"

    numSigs = verifier.NumSignatures
    verifyIdx = 0
    while verifyIdx < numSigs:
        verifier.Selector = verifyIdx
        verified = verifier.VerifySignature(True)
        if (verified != True):
            print(verifier.LastErrorText)
            sys.exit()

        verifyIdx = verifyIdx + 1

    print("All signatures were successfully verified.")
    signed_file = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": signedxmlll,
            "attached_to_doctype": "Sales Invoice",
            "attached_to_name": invoice_id,

            "content": signedd_xml,
        }
    )
    signed_file.save()

    return signed_file


def hashing_invoice(invoice_id):
    # Remove The following tags from the XML file (UBLExtension, QR, Signature)
    import xml.etree.ElementTree as ET

    cwd = os.getcwd()
    site = frappe.local.site

    attachments = frappe.get_all("File", fields=("name", "file_name", "attached_to_name", "file_url"),
                                 filters={"attached_to_name": ("in", invoice_id),
                                          "attached_to_doctype": "Sales Invoice"})

    for attachment in attachments:
        if attachment.file_name and attachment.file_name.endswith(".xml"):
            file_url = attachment.file_url

    file_url = f"{cwd}/{site}/public/{file_url}"
    tree = ET.parse(file_url)
    root = tree.getroot()
    for child in root:
        if child.tag.find("UBLExtensions") or child.tag.find("Signature") or child.tag.find("QR"):
            root.remove(child)

    # Hash the new invoice body using SHA-256
    clear_xml = ET.tostring(root, encoding='utf8', xml_declaration=False)
    invoice_hash = hashlib.sha256(clear_xml).hexdigest()
    try:
        invoice_hash = base64.b64decode(invoice_hash)
    except Exception as e:
        return None
    return bytes.hex(invoice_hash)


def sign_invoice(xml_filename, business_setting_id):
    try:
        settings = frappe.get_doc('ZATCA Business Settings', business_setting_id)
        xml_filename = xml_filename
        signed_xml_file_name = 'signedXml.xml'
        sdk_root = settings.sdk_root
        path_string = f"export SDK_ROOT={sdk_root} && export FATOORA_HOME=$SDK_ROOT/Apps && export PATH=$PATH:$FATOORA_HOME && cd $FATOORA_HOME "

        command_sign_invoice = path_string + f'fatoora -sign -invoice {xml_filename} -signedInvoice {signed_xml_file_name}'
    except Exception as e:
        frappe.throw("While signing invoice An error occurred, inside sign_invoice : " + str(e))

    try:
        err, out = _execute_in_shell(command_sign_invoice)

        match = re.search(r'ERROR', err.decode("utf-8"))
        if match:
            frappe.throw(err)

        match = re.search(r'ERROR', out.decode("utf-8"))
        if match:
            frappe.throw(out)

        match = re.search(r'INVOICE HASH = (.+)', out.decode("utf-8"))
        if match:
            invoice_hash = match.group(1)
            # frappe.msgprint("Xml file signed successfully and formed the signed xml invoice hash as : " + invoice_hash)
            return signed_xml_file_name, path_string
        else:
            frappe.throw(err, out)
    except Exception as e:
        frappe.throw("An error occurred sign invoice : " + str(e))


# TODO: Digital Signature Generation Implement
def generate_digital_signature(invoice_hash):
    cwd = os.getcwd()
    site = frappe.local.site
    new_path = f"{cwd}/{site}/private/files"
    Path(new_path).chdir()
    with open("privatekey.pem", "r") as file:
        privkey = file.read()
        privkey = clean_up_private_key_string(privkey)
    try:
        # private_key = SigningKey.from_string(private_key_bytes, curve=SECP256k1)
        # digital_signature = private_key.sign(invoice_has)
        pass
    except Exception as e:
        pass

    return "digital_signature"


def generate_hashing_certificate():
    encoded_hashed_cert = None
    cwd = os.getcwd()
    site = frappe.local.site
    new_path = f"{cwd}/{site}/private/files"
    Path(new_path).chdir()
    with open("cert.pem", "r") as file:
        cert = file.read()
        cert = clean_up_certificate_string(cert).encode('utf-8')
    try:
        hashed_cert = hashlib.sha256(cert).hexdigest()
        encoded_hashed_cert = base64.b64encode(bytes.fromhex(hashed_cert))
    except Exception as e:
        pass

    return encoded_hashed_cert


def clean_up_private_key_string(private_key_string):
    return private_key_string.replace("-----BEGIN EC PRIVATE KEY-----\n", "").replace("-----END EC PRIVATE KEY-----",
                                                                                      "").strip()


def clean_up_csr_string(certificate_string):
    return certificate_string.replace("-----BEGIN CERTIFICATE REQUEST-----\n", "").replace(
        "-----END CERTIFICATE REQUEST-----", "").strip()


def clean_up_certificate_string(certificate_string):
    return certificate_string.replace("-----BEGIN CERTIFICATE-----\n", "").replace("-----END CERTIFICATE-----",
                                                                                   "").strip()


def _execute_in_shell(cmd, verbose=False, low_priority=False, check_exit_code=False):
    # using Popen instead of os.system - as recommended by python docs
    import shlex
    import tempfile
    from subprocess import Popen
    env_variables = {"MY_VARIABLE": "some_value", "ANOTHER_VARIABLE": "another_value"}
    if isinstance(cmd, list):
        # ensure it's properly escaped; only a single string argument executes via shell
        cmd = shlex.join(cmd)
        # process = subprocess.Popen(command_sign_invoice, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env_variables)
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        kwargs = {"shell": True, "stdout": stdout, "stderr": stderr}
        if low_priority:
            kwargs["preexec_fn"] = lambda: os.nice(10)
        p = Popen(cmd, **kwargs)
        exit_code = p.wait()
        stdout.seek(0)
        out = stdout.read()
        stderr.seek(0)
        err = stderr.read()
    failed = check_exit_code and exit_code

    if verbose or failed:
        if err:
            frappe.msgprint(err)
        if out:
            frappe.msgprint(out)
    if failed:
        raise Exception("Command failed")
    return err, out
