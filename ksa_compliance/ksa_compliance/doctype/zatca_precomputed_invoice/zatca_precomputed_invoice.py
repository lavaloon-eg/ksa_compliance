# Copyright (c) 2024, LavaLoon and contributors
# For license information, please see license.txt
from typing import cast, Optional

import frappe
from frappe import _
from frappe.model.document import Document


class ZATCAPrecomputedInvoice(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        device_id: DF.Data | None
        invoice_counter: DF.Data | None
        invoice_hash: DF.Data | None
        invoice_qr: DF.SmallText | None
        invoice_uuid: DF.Data | None
        invoice_xml: DF.LongText | None
        previous_invoice_hash: DF.Data | None
        sales_invoice: DF.Link | None
    # end: auto-generated types
    pass

    @staticmethod
    def for_invoice(invoice_id: str) -> Optional['ZATCAPrecomputedInvoice']:
        prepared_id = frappe.db.exists({'doctype': 'ZATCA Precomputed Invoice', 'sales_invoice': invoice_id})
        if not prepared_id:
            return None

        return cast('ZATCAPrecomputedInvoice', frappe.get_doc('ZATCA Precomputed Invoice', prepared_id))

    def on_trash(self) -> None:
        frappe.throw(
            msg=_('You cannot Delete a configured ZATCA Precomputed Invoice'), title=_('This Action Is Not Allowed')
        )


@frappe.whitelist()
def download_xml(id: str):
    """
    Frappe doesn't know how to display an XML field without escaping it, so we made the field hidden. The only way
    for users to view the XML is to download it through this endpoint
    """
    doc = cast(ZATCAPrecomputedInvoice, frappe.get_doc('ZATCA Precomputed Invoice', id))

    # Reference: https://frappeframework.com/docs/user/en/python-api/response
    frappe.response.filename = doc.name + '.xml'
    frappe.response.filecontent = doc.invoice_xml
    frappe.response.type = 'download'
    frappe.response.display_content_as = 'attachment'
