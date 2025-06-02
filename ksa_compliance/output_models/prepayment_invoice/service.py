from frappe import _
import frappe

from .abs import PrepaymentInvoiceAbs
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry

from .factory.prepayment_invoice_factory import PrepaymentInvoiceFactory

class PrePaymentServiceImp(PrepaymentInvoiceAbs):

    def __init__(self):
        self.prepayment_invoice_factory = PrepaymentInvoiceFactory()


    def validate_prepayment_invoice(self, result: dict, doc : SalesInvoice |  PaymentEntry) -> None:
        if doc.doctype == 'Payment Entry':
            return
        if doc.doctype == 'POS Invoice':
            return
        if doc.doctype == 'Sales Invoice' and not doc.advances:
            return
        self.validate_prepayment_invoice_is_sent(doc)
        # may be i would need some filtering on result to be implemented
        zatca_fields_dto = result
        result["prepayment_invoice"] = self.prepayment_invoice_factory.create(zatca_fields_dto, doc)
        frappe.msgprint(str(result["prepayment_invoice"]))

    def validate_prepayment_invoice_is_sent(self, doc: SalesInvoice) -> None:
        for advance in doc.advances:
            custom_prepayment_invoice = frappe.db.get_value(
                advance.reference_type,
                advance.reference_name,
                "custom_prepayment_invoice",
            )
            if custom_prepayment_invoice:
                continue
            else:
                frappe.throw(
                    _("Please send prepayment invoice for {0} before submitting.").format(doc.name),
                    alert=True,
                )