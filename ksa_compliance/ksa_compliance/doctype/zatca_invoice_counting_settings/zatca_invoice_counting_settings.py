# Copyright (c) 2024, LavaLoon and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ZATCAInvoiceCountingSettings(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        business_settings_reference: DF.Link | None
        invoice_counter: DF.Int
        previous_invoice_hash: DF.Data | None
        zatca_egs: DF.Link | None
    # end: auto-generated types

    def on_trash(self) -> None:
        frappe.throw(
            msg=_('You cannot delete a configured Invoice Counting Settings'), title=_('This Action Is Not Allowed')
        )
