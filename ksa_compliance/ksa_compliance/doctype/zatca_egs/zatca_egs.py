# Copyright (c) 2024, LavaLoon and contributors
# For license information, please see license.txt
from typing import cast

import frappe
from frappe import _
from frappe.model.document import Document


class ZATCAEGS(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        business_settings: DF.Link
        compliance_request_id: DF.Data | None
        csr: DF.SmallText | None
        egs_type: DF.Literal['ERPNext', 'POS Device']
        enable_zatca_integration: DF.Check
        production_request_id: DF.Data | None
        production_secret: DF.Password | None
        production_security_token: DF.SmallText | None
        secret: DF.Password | None
        security_token: DF.SmallText | None
        sync_with_zatca: DF.Literal['Live', 'Batches']
        unit_common_name: DF.Data
        unit_serial: DF.Data
        validate_generated_xml: DF.Check
    # end: auto-generated types

    @property
    def is_live_sync(self) -> bool:
        return self.sync_with_zatca.lower() == 'live'

    @staticmethod
    def for_device(device_id: str) -> 'ZATCAEGS | None':
        egs = cast(str | None, frappe.db.exists('ZATCA EGS', {'unit_common_name': device_id}))
        if egs:
            return cast(ZATCAEGS, frappe.get_doc('ZATCA EGS', egs))

        return None

    def on_trash(self) -> None:
        frappe.throw(msg=_('You cannot Delete a configured ZATCA EGS'), title=_('This Action Is Not Allowed'))
