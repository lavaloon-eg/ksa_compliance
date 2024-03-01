import frappe

from ksa_compliance import logger
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings


def create_sales_invoice_additional_fields_doctype(self, method):
    settings = ZATCABusinessSettings.for_invoice(self.name)
    if not settings:
        logger.info(f"Skipping additional fields for sales invoice {self.name} because of missing ZATCA settings")
        return

    if not settings.has_production_csid:
        logger.info(f"Skipping additional fields for sales invoice {self.name} because of missing production CSID")
        return

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

    # We have to insert before submitting to ensure we can properly update the document with the hash, XML, etc.
    if settings.is_live_sync:
        si_additional_fields_doc.insert()
        si_additional_fields_doc.submit()
    else:
        si_additional_fields_doc.integration_status = "Ready For Batch"
        si_additional_fields_doc.insert()
