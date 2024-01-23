import frappe
import json


# import lxml.etree as ET


@frappe.whitelist(allow_guest=True)
def generate_xml():
    data = frappe.request.data or {}
    data = json.loads(data)

    # render XML Template
    invoice_xml = frappe.render_template(
        "ksa_compliance/ksa_compliance/e_invoice.xml",
        context={"invoice": data, "seller": {}, "buyer": {}, "business_settings": {}},
        is_path=True
    )
    invoice_xml = invoice_xml.replace("&", "&amp;")

    return invoice_xml
