from dataclasses import dataclass
from enum import Enum
from typing import Literal, List
import frappe
from frappe import _


class InvoiceMode(Enum):
    Auto = 'Let the system decide (both)'
    Simplified = 'Simplified Tax Invoices'
    Standard = 'Standard Tax Invoices'

    @staticmethod
    def from_literal(mode: str) -> 'InvoiceMode':
        for value in InvoiceMode:
            if value.value == mode:
                return value
        raise ValueError(f'Unknown value: {mode}')


InvoiceType = Literal['Standard', 'Simplified']


@dataclass
class InvoiceDiscountReason:
    name: str | None
    code: int | None


ZATCA_DISCOUNT_REASONS = [
    InvoiceDiscountReason(_('Bonus for works ahead of schedule'), 41),
    InvoiceDiscountReason(_('Other bonus'), 42),
    InvoiceDiscountReason(_("Manufacturer's consumer discount"), 60),
    InvoiceDiscountReason(_('Due to military status'), 62),
    InvoiceDiscountReason(_('Due to work accident'), 63),
    InvoiceDiscountReason(_('Special agreement'), 64),
    InvoiceDiscountReason(_('Production error discount'), 65),
    InvoiceDiscountReason(_('New outlet discount'), 66),
    InvoiceDiscountReason(_('Sample discount'), 67),
    InvoiceDiscountReason(_('End of range discount'), 68),
    InvoiceDiscountReason(_('Incoterm discount'), 70),
    InvoiceDiscountReason(_('Point of sales threshold allowance'), 71),
    InvoiceDiscountReason(_('Material surcharge/deduction'), 88),
    InvoiceDiscountReason(_('Discount'), 95),
    InvoiceDiscountReason(_('Special rebate'), 100),
    InvoiceDiscountReason(_('Fixed long term'), 102),
    InvoiceDiscountReason(_('Temporary'), 103),
    InvoiceDiscountReason(_('Standard'), 104),
    InvoiceDiscountReason(_('Yearly turnover'), 105),
]


@frappe.whitelist()
def get_zatca_invoice_discount_reason_list() -> List[str]:
    return [v.name for v in ZATCA_DISCOUNT_REASONS]


def get_zatca_discount_reason_by_name(name: str) -> InvoiceDiscountReason:
    return next((v for v in ZATCA_DISCOUNT_REASONS if v.name == name), InvoiceDiscountReason(None, None))
