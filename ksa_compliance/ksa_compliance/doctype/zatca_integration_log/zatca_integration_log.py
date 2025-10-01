# Copyright (c) 2024, Lavaloon and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ZATCAIntegrationLog(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        e_invoice_file: DF.Attach | None
        invoice_additional_fields_reference: DF.Link
        invoice_doctype: DF.Literal['Sales Invoice', 'POS Invoice', 'Payment Entry']
        invoice_reference: DF.DynamicLink
        status: DF.Literal[
            '',
            'Pending',
            'Resend',
            'Accepted with warnings',
            'Accepted',
            'Rejected',
            'Clearance switched off',
            'Duplicate',
        ]
        zatca_http_status_code: DF.Int
        zatca_message: DF.LongText | None
        zatca_status: DF.Data | None
    # end: auto-generated types
    pass

    def autoname(self):
        count = len(frappe.get_all(self.doctype, {'invoice_reference': self.invoice_reference}, pluck='name'))
        self.name = f'log-{self.invoice_reference}-{count + 1}'
