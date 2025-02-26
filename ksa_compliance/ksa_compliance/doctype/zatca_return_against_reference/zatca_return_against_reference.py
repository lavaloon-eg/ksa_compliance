from frappe.model.document import Document


class ZATCAReturnAgainstReference(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        parent: DF.Data
        parentfield: DF.Data
        parenttype: DF.Data
        sales_invoice: DF.Link
    # end: auto-generated types
    pass
