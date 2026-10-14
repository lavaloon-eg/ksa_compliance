"""Test data for the ZATCA rule tests: a company set up the way ksa_compliance needs, and its invoices."""

from dataclasses import dataclass

import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

from ksa_compliance.tests.scenarios import EXEMPT, OUT_OF_SCOPE, STANDARD, ZERO_RATED, Scenario

PREFIX = 'ZATCA Rules Test'
COMPANY = f'{PREFIX} Company'
CUSTOMER = f'{PREFIX} Customer'
# ERPNext's regional VAT override looks rates up by item code, so each category gets its own item.
ITEMS = {category: f'{PREFIX} {category} Item' for category in (STANDARD, ZERO_RATED, EXEMPT, OUT_OF_SCOPE)}
# ZATCA fields of each category's 0% Item Tax Template. Export reasons are avoided: ksa_compliance refuses
# to mix them with other categories on one invoice.
ZERO_VAT_CATEGORY_FIELDS = {
    ZERO_RATED: {'custom_zatca_item_tax_category': 'Zero rated goods || The international transport of Goods'},
    EXEMPT: {
        'custom_zatca_item_tax_category': 'Exempt from Tax || Financial services mentioned in Article 29 of the VAT '
        'Regulations'
    },
    OUT_OF_SCOPE: {
        'custom_zatca_item_tax_category': 'Services outside scope of tax / Not subject to VAT || {manual entry}',
        'custom_category_reason': 'Not subject to VAT',
    },
}


@dataclass(frozen=True)
class TaxTemplates:
    sales_taxes: str
    """The 15% Sales Taxes and Charges Template every invoice uses."""
    zero_vat_items: dict[str, str]
    """The 0% Item Tax Template of each non-standard category."""


def make_test_data() -> TaxTemplates:
    if not frappe.db.exists('Country', 'Saudi Arabia'):
        _insert('Country', country_name='Saudi Arabia', code='sa')
    _insert('Company', company_name=COMPANY, abbr='ZRT', default_currency='SAR', country='Saudi Arabia')
    _insert('Customer', customer_name=CUSTOMER)
    for item_code in ITEMS.values():
        _insert('Item', item_code=item_code, item_group='All Item Groups', is_stock_item=0, stock_uom='Nos')
    _make_business_settings()

    vat_account = _insert(
        'Account',
        account_name=f'{PREFIX} VAT',
        parent_account=frappe.db.get_value('Account', {'company': COMPANY, 'account_name': 'Duties and Taxes'}),
        company=COMPANY,
        account_type='Tax',
    )
    standard_rate = _insert('Tax Category', title=f'{PREFIX} Standard Rate', custom_zatca_category='Standard rate')
    return TaxTemplates(
        sales_taxes=_insert(
            'Sales Taxes and Charges Template',
            title=f'{PREFIX} VAT 15',
            company=COMPANY,
            tax_category=standard_rate,
            taxes=[{'charge_type': 'On Net Total', 'account_head': vat_account, 'rate': 15, 'description': 'VAT 15%'}],
        ),
        zero_vat_items={
            category: _insert(
                'Item Tax Template',
                title=f'{PREFIX} {category}',
                company=COMPANY,
                taxes=[{'tax_type': vat_account, 'tax_rate': 0}],
                **fields,
            )
            for category, fields in ZERO_VAT_CATEGORY_FIELDS.items()
        },
    )


def make_invoice(scenario: Scenario, templates: TaxTemplates) -> SalesInvoice:
    invoice = frappe.new_doc('Sales Invoice')
    invoice.update(
        {
            'company': COMPANY,
            'customer': CUSTOMER,
            'currency': 'SAR',
            'disable_rounded_total': 1,
            'taxes_and_charges': templates.sales_taxes,
            'is_return': int(scenario.is_return),
            'custom_return_reason': 'Goods returned' if scenario.is_return else None,
        }
    )
    sign = -1 if scenario.is_return else 1
    for line in scenario.lines:
        invoice.append(
            'items',
            {
                'item_code': ITEMS[line.category],
                'qty': sign * line.qty,
                'rate': line.price,
                'item_tax_template': templates.zero_vat_items.get(line.category),
            },
        )
    invoice.set_missing_values()
    invoice.set_taxes()
    invoice.taxes[0].included_in_print_rate = int(scenario.tax_included)
    return invoice.save()


def _insert(doctype: str, **fields) -> str:
    return frappe.get_doc({'doctype': doctype, **fields}).insert().name


def _make_business_settings():
    frappe.get_doc(
        {
            'doctype': 'ZATCA Business Settings',
            'company': COMPANY,
            'company_unit': f'{PREFIX} Unit',
            'company_unit_serial': '1-ERPNext|2-15|3-1',
            'company_category': f'{PREFIX} Category',
            'country_code': 'SA',
            'country': 'Saudi Arabia',
            'currency': 'SAR',
            'street': 'Test Street',
            'building': '1101',
            'city': 'Riyadh',
            'postal_code': '12345',
            'district': 'Test District',
            'seller_name': COMPANY,
            'vat_registration_number': '399999999900003',
        }
    ).insert(ignore_mandatory=True, ignore_links=True)
