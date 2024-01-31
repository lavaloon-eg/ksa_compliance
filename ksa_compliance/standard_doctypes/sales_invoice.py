import frappe


def create_sales_invoice_additional_fields_doctype(self, method):
    si_additional_fields_doc = frappe.new_doc("Sales Invoice Additional Fields")
    si_additional_fields_doc.sales_invoice = self.name
    if self.customer_address:
        customer_address_doc = frappe.get_doc("Address", self.customer_address)
        address_info = {
            "buyer_additional_number": "not available for now",
            "buyer_street_name": customer_address_doc.get("address_line1"),
            "buyer_additional_street_name": customer_address_doc.get("address_line2"),
            "buyer_building_number": customer_address_doc.get("custom_building_number"),
            "buyer_city": customer_address_doc.get("city"),
            "buyer_postal_code": customer_address_doc.get("pincode"),
            "buyer_district": customer_address_doc.get("custom_area"),
            "buyer_country_code": customer_address_doc.get("country"),
        }
        si_additional_fields_doc.update(address_info)
    si_additional_fields_doc.submit()
