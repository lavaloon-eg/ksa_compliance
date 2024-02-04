import base64
import hashlib
import os
import re

import requests
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from subprocess import call

import frappe
import json
from frappe.utils.logger import get_logger


def generate_xml(input_data: dict = None, invoice_type: str = "Simplified"):
    """
    For postman testing purpose
    """
    data = input_data or frappe.request.data
    if not isinstance(data, dict):
        data = json.loads(data)

    template = "simplified_e_invoice.xml" if invoice_type.lower() == "simplified" else "standard_e_invoice.xml"

    # render XML Template
    invoice_xml = frappe.render_template(
        f"ksa_compliance/templates/{template}",
        context={"invoice": data.get("invoice"), "seller_details": data.get("seller_details"),
                 "buyer_details": data.get("buyer_details"),
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

    base64_invoice, invoice_hash_bytes = hashing_invoice(data["invoice"]["id"])
    digital_signature = generate_digital_signature(invoice_hash_bytes)  # TODO: Need investigation to implement
    encoded_hashed_certificate, cert_bytes = generate_hashing_certificate()
    base64_properties_hash, properties_hash_bytes = populate_signed_properties_output(file.file_name,
                                                                                      encoded_hashed_certificate,
                                                                                      cert_bytes)
    signed_invoice_xml = generate_signed_xml_file(data["invoice"]["id"], file.file_name, base64_invoice,
                                                  digital_signature, cert_bytes, base64_properties_hash)

    return base64_invoice, signed_invoice_xml


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
    from path import Path
    logger = get_logger("csr-generation")
    try:
        settings = frappe.get_doc('ZATCA Business Settings', business_settings_id)
        csr_config_file = 'csrconfig.txt'
        privatekey_file = "privatekey.pem"
        pubkey_file = "pubkey.pem"
        cwd = os.getcwd()
        site = frappe.local.site

        Path(f"{cwd}/{site}").chdir()

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

        Path(cwd).chdir()

    except Exception as e:
        Path(cwd).chdir()
        frappe.throw("error occurred in generate csr" + str(e))


@frappe.whitelist(allow_guest=True)
def create_CSID(business_settings_id):
    from path import Path
    try:
        settings = frappe.get_doc("ZATCA Business Settings", business_settings_id)
        cwd = os.getcwd()
        site = frappe.local.site

        Path(f"{cwd}/{site}").chdir()

        with open(r'taxpayerCSRbase64Encoded.txt', 'r') as file:
            data = file.read()
            data = data.replace("\n", "")
            data = data.replace("\r", "")

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
        decoded_bin = base64.b64decode(data["binarySecurityToken"]).decode("utf-8")

        with open(f"cert.pem", 'w') as file:  # attaching X509 certificate
            file.write(decoded_bin)

        settings.set("basic_auth", encoded_value)
        settings.save(ignore_permissions=True)
        settings.set("compliance_request_id", data["requestID"])
        settings.save(ignore_permissions=True)
        Path(cwd).chdir()

    except Exception as e:
        Path(cwd).chdir()
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


def populate_signed_properties_output(file_name, encoded_cert, bytes_cert):
    from path import Path
    import xml.etree.ElementTree as ET

    certificate = x509.load_pem_x509_csr(bytes_cert, default_backend())
    final_required_data = extract_info_from_certificate(certificate)
    cwd = os.getcwd()
    site = frappe.local.site
    file_url = f"{cwd}/{site}/public/files/{file_name}"
    tree = ET.parse(file_url)
    root = tree.getroot()
    for child in root:
        if child.tag.find("UBLExtensions") or child.tag.find("Signature") or child.tag.find("QR"):
            root.remove(child)

    # Start Population
    ubl_extensions = ET.SubElement(root, "ext:UBLExtensions")
    ubl_extension = ET.SubElement(ubl_extensions, "ext:UBLExtension")
    extension_content = ET.SubElement(ubl_extension, "ext:ExtensionContent")
    ubl_document_signatures = ET.SubElement(extension_content, "sig:UBLDocumentSignatures")
    signature_information = ET.SubElement(ubl_document_signatures, "sac:SignatureInformation")
    signature = ET.SubElement(signature_information, "ds:Signature")
    ds_object = ET.SubElement(signature, "ds:Object")
    qualifying_properties = ET.SubElement(ds_object, "xades:QualifyingProperties")
    signed_properties = ET.SubElement(qualifying_properties, "xades:SignedProperties")
    signed_signature_properties = ET.SubElement(signed_properties, "xades:SignedSignatureProperties")
    signing_certificate = ET.SubElement(signed_signature_properties, "xades:SigningCertificate")
    xades_cert = ET.SubElement(signing_certificate, "xades:Cert")
    cert_digest = ET.SubElement(xades_cert, "xades:CertDigest")
    digest_value = ET.SubElement(cert_digest, "ds:DigestValue")  # Encoded Certificate
    digest_value.text = encoded_cert
    signing_time = ET.SubElement(signed_signature_properties, "xades:SigningTime")  # Signing Time
    signing_time.text = "2024-01-24T11:36:34Z"
    issuer_serial = ET.SubElement(xades_cert, "xades:IssuerSerial")
    x509_issuer_name = ET.SubElement(issuer_serial, "ds:X509IssuerName")  # Issuer Name
    x509_issuer_name.text = final_required_data.get("organizationName")
    x509_serial_number = ET.SubElement(issuer_serial, "ds:X509SerialNumber")  # Issuer Serial Number
    x509_serial_number.text = final_required_data.get("surname")

    tree.write(file_name)
    clear_xml = ET.tostring(root, encoding='utf-8', xml_declaration=False)

    properties_hash = hashlib.sha256(clear_xml)  # Hash the invoice using SHA 256
    properties_hash_bytes = properties_hash.digest()  # Extract invoice bytes from hashed invoice
    properties_hex = properties_hash.hexdigest()  # Invoice Hexadecimal
    base64_properties_hash = base64.b64encode(properties_hash_bytes).decode("utf-8")  # Encode the invoice using base64
    return base64_properties_hash, properties_hash_bytes


def generate_signed_xml_file(invoice_id, file_name, base64_invoice, digital_signature, encoded_cert,
                             base64_properties_hash):
    from path import Path
    import xml.etree.ElementTree as ET

    cwd = os.getcwd()
    site = frappe.local.site
    new_path = f"{cwd}/{site}"
    Path(new_path).chdir()
    with open("cert.pem", "r") as file:
        cert = file.read()

    Path(cwd).chdir()

    signed_xml_file_name = "signedXml" + file_name
    file_url = f"{cwd}/{site}/public/files/{file_name}"
    tree = ET.parse(file_url)
    root = tree.getroot()
    # Start UBL STATIC DATA
    clear_XML = ET.tostring(root, encoding="utf-8")
    ubl_extensions = ET.SubElement(root, '{urn:oasis:names:specification:ubl:dsig:enveloped:xades}UBLExtensions')
    ubl_extension = ET.SubElement(ubl_extensions,
                                  "{urn:oasis:names:specification:ubl:dsig:enveloped:xades}UBLExtension")
    extension_uri = ET.SubElement(ubl_extension, "{urn:oasis:names:specification:ubl:dsig:enveloped:xades}ExtensionURI")
    extension_uri.text = "urn:oasis:names:specification:ubl:dsig:enveloped:xades"
    extension_content = ET.SubElement(ubl_extension,
                                      "{urn:oasis:names:specification:ubl:dsig:enveloped:xades}ExtensionContent")
    ubl_document_signatures = ET.SubElement(extension_content, "sig:UBLDocumentSignatures")
    ubl_document_signatures.set("xmlns:sig", "urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2")
    ubl_document_signatures.set("xmlns:sac",
                                "urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2")
    ubl_document_signatures.set("xmlns:sbc", "urn:oasis:names:specification:ubl:schema:xsd:SignatureBasicComponents-2")
    signature_information = ET.SubElement(ubl_document_signatures, "sac:SignatureInformation")
    signature_id = ET.SubElement(signature_information, "{urn:oasis:names:specification:ubl:signature:1}ID")
    referenced_signature_id = ET.SubElement(signature_information,
                                            "{urn:oasis:names:specification:ubl:signature:Invoice}ReferencedSignatureID")
    signature = ET.SubElement(signature_information, "ds:Signature")
    signature.set("Id", "signature")
    signature.set("xmlns:ds", "http://www.w3.org/2000/09/xmldsig#")

    signature_value = ET.SubElement(signature, "ds:SignatureValue")
    signature_value.text = digital_signature  # Encoded Digital Signature

    signed_info = ET.SubElement(signature, "ds:SignedInfo")
    canonicalization_method = ET.SubElement(signed_info, "ds:CanonicalizationMethod")
    canonicalization_method.set("Algorithm", "http://www.w3.org/2006/12/xml-c14n11")
    signature_method = ET.SubElement(signed_info, "ds:SignatureMethod")
    signature_method.set("Algorithm", "http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha256")
    reference = ET.SubElement(signed_info, "ds:Reference")
    reference.set("Id", "invoiceSignedData")

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
    digest_value.text = base64_invoice  # Encoded hashed invoice

    reference2 = ET.SubElement(signed_info, "ds:Reference")
    reference2.set("URI", "#xadesSignedProperties")
    reference2.set("Type", "http://www.w3.org/2000/09/xmldsig#SignatureProperties")

    digest_method1 = ET.SubElement(reference2, "ds:DigestMethod")
    digest_method1.set("Algorithm", "http://www.w3.org/2001/04/xmlenc#sha256")

    digest_value1 = ET.SubElement(reference2, "ds:DigestValue")
    digest_value1.text = base64_properties_hash  # Encoded properties hash

    key_info = ET.SubElement(signature, "ds:KeyInfo")
    x509_data = ET.SubElement(key_info, "ds:X509Data")
    x509_certificate = ET.SubElement(x509_data, "ds:X509Certificate")
    x509_certificate.text = cert  # Encoded Certificate

    try:
        tree.write(signed_xml_file_name)
        with open(signed_xml_file_name, "r") as file:
            invoice_xml = file.read()
        file = frappe.new_doc("File")
        data = {
            "file_name": signed_xml_file_name,
            "attached_to_doctype": "Sales Invoice",
            "attached_to_name": invoice_id,
            "content": invoice_xml,
        }
        file.update(data)
        file.insert()
    except Exception as e:
        pass

    return invoice_xml


def hashing_invoice(invoice_id):
    # Remove The following tags from the XML file (UBLExtension, QR, Signature)
    from lxml import etree as ET

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

    # Hash the new invoice body using SHA-256 and note the invoice is already Canonicalized using C14N
    canonical_xml = ET.tostring(root, method="c14n", exclusive=True, with_comments=False, xml_declaration=False)

    invoice_hash = hashlib.sha256(canonical_xml)  # Hash the invoice using SHA 256
    invoice_hash_bytes = invoice_hash.digest()  # Extract invoice bytes from hashed invoice
    base64_invoice_hash = base64.b64encode(invoice_hash_bytes).decode("utf-8")  # Encode the invoice using base64
    return base64_invoice_hash, invoice_hash_bytes


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


def generate_digital_signature(invoice_hash_bytes):
    from path import Path
    from ecdsa import SigningKey
    cwd = os.getcwd()
    site = frappe.local.site
    new_path = f"{cwd}/{site}"
    Path(new_path).chdir()
    with open("privatekey.pem", "rb") as file:
        privkey = SigningKey.from_pem(file.read())

    digital_signature = privkey.sign(invoice_hash_bytes)
    Path(cwd).chdir()
    return base64.b64encode(digital_signature).decode("utf-8")


def generate_hashing_certificate():
    from path import Path
    cwd = os.getcwd()
    site = frappe.local.site
    new_path = f"{cwd}/{site}"
    Path(new_path).chdir()
    with open("taxpayer.csr", "rb") as file:
        cert_bytes = file.read()

    ce = x509.load_pem_x509_csr(cert_bytes, default_backend())
    base64_cert_hash = base64.b64encode(ce.tbs_certrequest_bytes).decode("utf-8")
    Path(cwd).chdir()
    return base64_cert_hash, cert_bytes


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


def extract_info_from_certificate(certificate):
    final_data = {}
    subjects = certificate.subject
    for attr in subjects:
        final_data[attr.oid._name] = attr.value

    extensions = certificate.extensions  # To get serial number, uuid, address, title (invoice type), and industry
    for ext in extensions:
        if ext.oid == x509.ExtensionOID.SUBJECT_ALTERNATIVE_NAME:
            for alt_name in ext.value:
                for sub_extension in alt_name.value:
                    final_data[sub_extension.oid._name] = sub_extension.value

    return final_data
