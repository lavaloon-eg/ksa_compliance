import frappe
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings
from ksa_compliance.throw import fthrow
from frappe import _


def validate_branch_doctype(doc, method):
    validate_mandatory_crn(doc)
    validate_duplicate_crn(doc)


def validate_mandatory_crn(doc):
    if (
        doc.custom_branch_ids
        and doc.custom_company
        and ZATCABusinessSettings.is_branch_config_enabled(doc.custom_company)
    ):
        crn = doc.custom_branch_ids[0].value
        crn = crn.strip() or None if type(crn) is str else crn
        if not crn:
            fthrow(
                msg=_('CRN is mandatory when ZATCA branch configuration is enabled for company.'),
                title=_('Mandatory CRN'),
            )


def validate_duplicate_crn(doc):
    if doc.custom_branch_ids:
        crn = doc.custom_branch_ids[0].value
        if crn and frappe.db.exists(
            'Additional Seller IDs',
            {'parentfield': 'custom_branch_ids', 'parenttype': 'Branch', 'value': crn, 'parent': ['!=', doc.name]},
        ):
            fthrow(msg=_('This CRN is already used in another branch configuration.'), title=_('Duplicate CRN Error'))
