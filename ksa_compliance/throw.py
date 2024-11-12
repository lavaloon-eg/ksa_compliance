from typing import NoReturn

import frappe
from frappe import ValidationError


def fthrow(
    msg: str,
    exc: type[Exception] = ValidationError,
    title: str | None = None,
    is_minimizable: bool = False,
    wide: bool = False,
    as_list: bool = False,
) -> NoReturn:
    """
    A wrapper for frappe.throw that is annotated properly as having no return (i.e. throws an exception)

    frappe.throw is annotated as returning 'None' instead of 'NoReturn'. This messes up type analysis, especially with
    result type. For example, the following code:

        if is_err(result):
            frappe.throw("An error occurred")

        frappe.msgprint(result.ok_value)

    The msgprint would result in an analysis warning because the analyzer doesn't see that the error case ends
    at the throw. We'd have to use an explicit else, which causes unnecessary nesting.
    """
    frappe.throw(msg, exc, title, is_minimizable, wide, as_list)
