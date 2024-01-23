import frappe
from ksa_compliance.output_models.business_settings_output_model import Einvoice


@frappe.whitelist(allow_guest=True)
def generate_xml():
    import json
    data = frappe.request.data or {}
    # if isinstance(data, str):
    data = json.loads(data)

    postman_data_input = data

    sales_doc = {"key": "value"}
    # Construct output model
    final_result = Einvoice(sales_invoice_additional_fields_doc=sales_doc)

    # print("\n\n\n", final_result.party_identification, "\n\n\n")
    print("\n\n\n", final_result.data, "\n\n\n")
    return final_result.result, final_result.error_dic
