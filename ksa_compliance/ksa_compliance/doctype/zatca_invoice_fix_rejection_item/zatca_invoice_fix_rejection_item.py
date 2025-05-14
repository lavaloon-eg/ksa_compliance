# Copyright (c) 2025, LavaLoon and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ZATCAInvoiceFixRejectionItem(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        amount_without_taxes: DF.Float
        discount_amount: DF.Float
        fixed_amount_without_taxes: DF.Float
        fixed_discount_amount: DF.Float
        fixed_tax_amount: DF.Float
        item: DF.Link | None
        parent: DF.Data
        parentfield: DF.Data
        parenttype: DF.Data
        qty: DF.Float
        tax_amount: DF.Float
    # end: auto-generated types
    pass
