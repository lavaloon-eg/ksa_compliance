import frappe
import json


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
    return invoice_xml


def generate_einvoice_xml_fielname(business_settings, invoice):
    vat_registration_number = business_settings["company_id"]
    invoice_date = invoice["issue_date"].replace("-", "")
    invoice_time = invoice["issue_time"].replace(":", "")
    invoice_number = invoice["id"]
    file_name = vat_registration_number + "_" + invoice_date + "T" + invoice_time + "_" + invoice_number
    progressive_name = frappe.model.naming.make_autoname(file_name)
    progressive_name = progressive_name[:len(file_name)]
    return progressive_name + ".xml"
