import json

import frappe

from ksa_compliance.invoice import InvoiceType


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

    invoice_xml = invoice_xml.replace("\n", "")
    return invoice_xml


def generate_xml_file(data: dict, invoice_type: InvoiceType = "Simplified"):
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
    return invoice_xml


def generate_einvoice_xml_fielname(vat_registration_number: str, issue_date: str, issue_time: str, invoice_number: str):
    file_name = (vat_registration_number + "_" + issue_date + "T" + issue_time.replace(':',
                                                                                       '') + "_" + invoice_number +
                 ".xml")
    return file_name
