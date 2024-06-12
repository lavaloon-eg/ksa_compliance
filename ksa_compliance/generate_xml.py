import json

import frappe


@frappe.whitelist(allow_guest=True)
def generate_xml(input_data: dict = None):
    """
    For postman testing purpose
    """
    data = input_data or frappe.request.data
    if not isinstance(data, dict):
        data = json.loads(data)

    # render XML Template
    invoice_xml = frappe.render_template(
        "ksa_compliance/templates/e_invoice.xml",
        context={"invoice": data.get("invoice"), "seller": data.get("seller"), "buyer": data.get("buyer"),
                 "business_settings": data.get("business_settings")},
        is_path=True
    )

    invoice_xml = invoice_xml.replace("\n", "")
    return invoice_xml


def generate_xml_file(data: dict):
    """
    For Generating cycle
    """
    # render XML Template
    invoice_xml = frappe.render_template(
        "ksa_compliance/templates/e_invoice.xml",
        context={
            "invoice": data.get("invoice"),
            "seller_details": data.get("seller_details"),
            "buyer_details": data.get("buyer_details"),
            "business_settings": data.get("business_settings")},
        is_path=True
    )
    return invoice_xml
