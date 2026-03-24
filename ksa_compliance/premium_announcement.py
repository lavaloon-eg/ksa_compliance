import json
from datetime import timedelta

import frappe
from frappe.model.utils.user_settings import get_user_settings, save
from frappe.utils import get_datetime, get_datetime_str


@frappe.whitelist()
def show_announcement(announcement_key: str, validate_date: bool = False) -> bool:
    if not frappe.session.user:
        return False

    if settings := get_user_settings('User'):
        settings = json.loads(settings)
        if date := settings.get(announcement_key):
            if validate_date:
                if get_datetime(date) > (get_datetime() - timedelta(days=14)):
                    return False
            else:
                return False
    return True


@frappe.whitelist()
def dismiss_premium_announcement(announcement_key: str):
    if not frappe.session.user:
        return None

    if settings := get_user_settings('User', for_update=True):
        settings = json.loads(settings)
        settings[announcement_key] = get_datetime_str(get_datetime())
        updated_settings = json.dumps(settings)
        save('User', updated_settings)

    return None
