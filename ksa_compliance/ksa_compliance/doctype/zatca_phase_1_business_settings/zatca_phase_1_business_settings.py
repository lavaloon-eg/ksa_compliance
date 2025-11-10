# Copyright (c) 2024, LavaLoon and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.data import get_link_to_form
from frappe.query_builder import DocType


class ZATCAPhase1BusinessSettings(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        address: DF.Link
        company: DF.Link
        status: DF.Literal['Active', 'Disabled']
        type_of_transaction: DF.Literal['Simplified Tax Invoice', 'Standard Tax Invoice', 'Both']
        vat_registration_number: DF.Data | None
    # end: auto-generated types
    pass

    def validate(self):
        business_settings_id = frappe.get_value(
            'ZATCA Business Settings',
            {
                'company': self.company,
                'status': 'Active',
            },
        )
        if business_settings_id and self.status == 'Active':
            link = get_link_to_form('ZATCA Business Settings', business_settings_id)
            frappe.throw(
                f'ZATCA Phase 2 Business Settings already enabled for company {self.company}: {link}',
                title='Another Setting Already Enabled',
            )

    @staticmethod
    def is_enabled_for_company(company_id: str) -> bool:
        return bool(
            frappe.db.get_value('ZATCA Phase 1 Business Settings', filters={'company': company_id, 'status': 'Active'})
        )


@frappe.whitelist()
def get_company_primary_address(company):
    dynamic_link = DocType('Dynamic Link')
    address = DocType('Address')
    query = (
        frappe.qb.from_(address)
        .select(address.name)
        .where(address.is_primary_address == 1)
        .join(dynamic_link)
        .on(address.name == dynamic_link.parent)
        .where(dynamic_link.link_name == company)
    ).run(as_dict=1)
    return query


@frappe.whitelist()
def get_all_company_addresses(company):
    return frappe.get_all(
        'Dynamic Link', filters={'link_name': company, 'parenttype': 'Address'}, fields=['parent'], pluck='parent'
    )
