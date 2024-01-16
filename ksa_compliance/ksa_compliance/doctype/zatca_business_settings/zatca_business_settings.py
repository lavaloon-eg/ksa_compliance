# Copyright (c) 2024, Lavaloon and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe.model.document import Document


class ZATCABusinessSettings(Document):
    pass


@frappe.whitelist()
def fetch_company_addresses(company_name):
    # company_list = frappe.db.sql(
    #     ''' SELECT parent
    #     	FROM `tabDynamic Link`
    #         WHERE link_name = '{}' '''.format(company_name))
    company_list_dict = frappe.get_all("Dynamic Link", filters={"link_name": company_name}, fields=["parent"])
    company_list = [address.parent for address in company_list_dict]
    print(company_list)
    return company_list
