import frappe
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings
from ksa_compliance.throw import fthrow
from ksa_compliance.translation import ft


def validate_branch(doc, method):
    validate_mandatory_crn(doc)
    warn_on_duplicate_crn(doc)


def validate_mandatory_crn(doc):
    """Validate CRN when present on a branch.

    When branch configuration is enabled, branches may optionally specify their own CRN
    via ``custom_branch_ids``. If a branch does not have a CRN, invoices for that branch
    will fall back to the seller IDs from ZATCA Business Settings. This supports the
    common scenario where most branches share the company's main Commercial Registration
    while only specific branches operate under a different one.
    """
    if (
        doc.custom_branch_ids
        and doc.custom_company
        and ZATCABusinessSettings.is_branch_config_enabled(doc.custom_company)
    ):
        crn = doc.custom_branch_ids[0].value
        crn = crn.strip() or None if isinstance(crn, str) else crn
        if not crn:
            fthrow(
                msg=ft('CRN is mandatory when ZATCA branch configuration is enabled for company.'),
                title=ft('Mandatory CRN'),
            )


def warn_on_duplicate_crn(doc):
    """
    Warns, without blocking, if another branch already uses the same CRN.

    Under the unified commercial registration (CR 2.0, in force from April 2025) a company has a single
    national CR covering all of its branches, so sharing one CRN across branches is expected rather than an
    error.
    """
    if doc.custom_branch_ids:
        crn = doc.custom_branch_ids[0].value
        crn_exists = frappe.db.exists(
            'Additional Seller IDs',
            {'parentfield': 'custom_branch_ids', 'parenttype': 'Branch', 'value': crn, 'parent': ['!=', doc.name]},
        )
        if crn and crn_exists:
            branch = frappe.get_value('Additional Seller IDs', crn_exists, 'parent')
            frappe.msgprint(
                msg=ft(
                    'This CRN is also configured for branch: $branch. This is expected if your company uses a '
                    'single unified commercial registration for all of its branches.',
                    branch=branch,
                ),
                title=ft('Duplicate CRN'),
                indicator='orange',
            )
