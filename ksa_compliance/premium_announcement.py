import json
from datetime import timedelta

import frappe
from frappe.model.utils.user_settings import get_user_settings, update_user_settings
from frappe.utils import get_datetime, get_datetime_str


@frappe.whitelist()
def should_show_announcement(announcement_key: str, validate_date: bool = False) -> bool:
    if not frappe.session.user:
        return False

    if settings := get_user_settings('User'):
        settings = json.loads(settings)
        if last_shown_date := settings.get(announcement_key):
            if validate_date:
                older_than_14_days = get_datetime(last_shown_date) < (get_datetime() - timedelta(days=14))
                return older_than_14_days
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
        update_user_settings('User', settings)

    return None
