from string import Template

import frappe


def ft(message: str, **kwargs) -> str:
    """
    Translates a template string using frappe._. Use $ prefix for template variables in the message, and pass the
    values as keyword arguments

    Example: ft("Could not open file '$path'", path=filepath)
    """
    # noinspection PyProtectedMember
    translated = frappe._(message)
    return Template(translated).substitute(kwargs) if kwargs else translated
