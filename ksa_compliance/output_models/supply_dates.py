"""Supply date (KSA-5) and supply end date (KSA-24) resolution.

By default, the supply date is read from the invoice `due_date`, which keeps the existing behaviour. Apps can point
either date to another field through hooks, e.g. in their hooks.py:

    zatca_supply_date_field = 'posting_date'
    zatca_supply_end_date_field = 'custom_supply_end_date'

If several apps define a hook, the last installed app wins. The supply end date is only emitted when its hook is set
and the invoice has a value in that field.
"""

from __future__ import annotations

from typing import Optional

import frappe

DEFAULT_SUPPLY_DATE_FIELD = 'due_date'


def _last_hook(name: str) -> Optional[str]:
    values = [v for v in frappe.get_hooks(name) or [] if v]
    return values[-1] if values else None


def get_supply_date_field() -> str:
    return _last_hook('zatca_supply_date_field') or DEFAULT_SUPPLY_DATE_FIELD


def get_supply_end_date_field() -> Optional[str]:
    return _last_hook('zatca_supply_end_date_field')
