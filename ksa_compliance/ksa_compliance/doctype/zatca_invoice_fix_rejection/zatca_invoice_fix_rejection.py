# Copyright (c) 2025, LavaLoon and contributors
# For license information, please see license.txt
from typing import Literal, cast

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from ksa_compliance.throw import fthrow
from ksa_compliance.translation import ft
import xml.etree.ElementTree as Et


class ZATCAInvoiceFixRejection(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from ksa_compliance.ksa_compliance.doctype.zatca_invoice_fix_rejection_item.zatca_invoice_fix_rejection_item import (
            ZATCAInvoiceFixRejectionItem,
        )

        fix_reason: DF.SmallText
        fixed_total_amount_with_taxes_and_discount: DF.Float
        fixed_total_amount_without_taxes: DF.Float
        fixed_total_amount_without_taxes_and_discount: DF.Float
        fixed_total_discount_amount: DF.Float
        fixed_total_tax_amount: DF.Float
        invoice: DF.DynamicLink | None
        invoice_type: DF.Literal['Sales Invoice', 'POS Invoice']
        items: DF.Table[ZATCAInvoiceFixRejectionItem]
        total_amount_with_taxes_and_discount: DF.Float
        total_amount_without_taxes: DF.Float
        total_amount_without_taxes_and_discount: DF.Float
        total_discount_amount: DF.Float
        total_tax_amount: DF.Float
    # end: auto-generated types


@frappe.whitelist()
def fetch_invoice_amounts_details(invoice_type: Literal['Sales Invoice', 'POS Invoice'], invoice: str):
    from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import (
        SalesInvoiceAdditionalFields,
    )

    additional_fields_id = frappe.db.exists(
        'Sales Invoice Additional Fields', {'invoice_doctype': invoice_type, 'sales_invoice': invoice}
    )
    if not additional_fields_id:
        fthrow(msg=ft("Sales invoice doesn't have additional fields"), title=ft('Invalid Invoice Error'))

    additional_fields_doc = cast(
        SalesInvoiceAdditionalFields, frappe.get_doc('Sales Invoice Additional Fields', additional_fields_id)
    )
    namespaces = {
        'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    }

    tree = Et.fromstring(additional_fields_doc.invoice_xml)
    total_amount_without_taxes_and_discount = flt(
        tree.find('.//cac:LegalMonetaryTotal/cbc:LineExtensionAmount', namespaces).text
    )
    total_amount_without_taxes = flt(tree.find('.//cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount', namespaces).text)
    total_amount_with_taxes_and_discount = flt(
        tree.find('.//cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount', namespaces).text
    )
    total_discount_amount = flt(tree.find('.//cac:LegalMonetaryTotal/cbc:AllowanceTotalAmount', namespaces).text)
    total_tax_amount = flt(tree.find('.//cac:TaxTotal/cbc:TaxAmount', namespaces).text)

    items = []
    invoice_lines = tree.findall('.//cac:InvoiceLine', namespaces)
    for item in invoice_lines:
        item_code = item.find('.//cac:Item/cbc:Name', namespaces).text

        qty = flt(item.find('.//cbc:InvoicedQuantity', namespaces).text)
        amount_without_taxes = flt(item.find('.//cbc:LineExtensionAmount', namespaces).text)
        tax_amount = flt(item.find('.//cac:TaxTotal/cbc:TaxAmount', namespaces).text)
        allowance_charge_el = item.find('.//cac:Price/cac:AllowanceCharge', namespaces)
        discount_amount = 0.00
        if allowance_charge_el:
            discount_amount = flt(allowance_charge_el.find('.//cbc:Amount', namespaces).text)

        items.append(
            {
                'item_code': item_code,
                'qty': qty,
                'amount_without_taxes': amount_without_taxes,
                'tax_amount': tax_amount,
                'discount_amount': discount_amount,
            }
        )

    return {
        'total_tax_amount': total_tax_amount,
        'total_amount_without_taxes_and_discount': total_amount_without_taxes_and_discount,
        'total_amount_without_taxes': total_amount_without_taxes,
        'total_amount_with_taxes_and_discount': total_amount_with_taxes_and_discount,
        'total_discount_amount': total_discount_amount,
        'items': items,
    }
