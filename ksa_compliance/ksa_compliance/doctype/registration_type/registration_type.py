# Copyright (c) 2024, Lavaloon and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class RegistrationType(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        type_code: DF.Data | None
        type_name: DF.Data | None
    # end: auto-generated types
    pass
