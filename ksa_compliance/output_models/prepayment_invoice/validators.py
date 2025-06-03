import frappe
from frappe import _


def validate_mandatory_fields(obj, field_rules: dict) -> None:
    """Generic mandatory field validator"""
    for field, error_msg in field_rules.items():
        if not getattr(obj, field, None):
            frappe.throw(_(error_msg), alert=True)
