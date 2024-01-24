import frappe


def create_sales_invoice_additional_fields_doctype(self, method):
    customer_address_doc = frappe.get_doc("Address", self.customer_address)

    sales_invoice_additional_fields_dict = {
        "doctype": "Sales Invoice Additional Fields",
        "sales_invoice": self.name,
        "buyer_street_name": customer_address_doc.get("address_line1"),
        "buyer_additional_street_name": customer_address_doc.get("address_line2"),
        "buyer_building_number": customer_address_doc.get("custom_building_number"),
        "buyer_additional_number": "not available for now",
        "buyer_city": customer_address_doc.get("city"),
        "buyer_postal_code": customer_address_doc.get("pincode"),
        "buyer_district": customer_address_doc.get("custom_area"),
        "buyer_country_code": customer_address_doc.get("country"),
    }
    additional_fields_doc = frappe.get_doc(sales_invoice_additional_fields_dict)
    additional_fields_doc.save()
