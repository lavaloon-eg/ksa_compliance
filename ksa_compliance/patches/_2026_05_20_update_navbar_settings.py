from typing import cast

import frappe
from frappe.core.doctype.navbar_settings.navbar_settings import NavbarSettings


def execute():
    navbar_settings = cast(NavbarSettings, frappe.get_single('Navbar Settings'))
    navbar_settings.append(
        'help_dropdown',
        {'item_label': 'KSA Compliance Premium', 'item_type': 'Route', 'route': '/app/ksa-compliance-premium'},
    )
    navbar_settings.save()
