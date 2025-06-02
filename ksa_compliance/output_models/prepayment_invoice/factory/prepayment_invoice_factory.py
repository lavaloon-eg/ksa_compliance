import frappe
from ..abs import Factory
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice


from .invoice_line_factory import InvoiceLineFactory
from ..domain.prepayment_invoice.prepayment_invoice import PrepaymentInvoiceBuilder
from ..factory.xml_factory import XMLTagFactory
from ..xml_tag import XMLTag


class PrepaymentInvoiceFactory(Factory):
    @staticmethod
    def create(zatca_fields_dto: dict, doc: SalesInvoice):
        prepaid_amount = PrepaymentInvoiceFactory._get_prepaid_amount(zatca_fields_dto, doc)
        currency = PrepaymentInvoiceFactory._get_currency(zatca_fields_dto, doc)
        return (
            PrepaymentInvoiceBuilder()
            .set_prepaid_amount(prepaid_amount)
            .set_currency(currency)
            .set_prepaid_amount_xml_tag(PrepaymentInvoiceFactory._get_xml_tag(currency, prepaid_amount))
            .set_invoice_lines(PrepaymentInvoiceFactory._get_invoice_lines(zatca_fields_dto, doc))
            .build()
        )

    @staticmethod
    def _get_invoice_lines(zatca_fields_dto: dict, doc: SalesInvoice):
        invoicelines = InvoiceLineFactory.create(zatca_fields_dto, doc)
        return invoicelines

    @staticmethod
    def _get_prepaid_amount(zatca_fields_dto: dict, doc: SalesInvoice) -> float:
        prepaid_amount = 0
        for row in doc.advances:
            tax_amount = frappe.db.get_value(
                row.reference_type,
                row.reference_name,
                'total_taxes_and_charges',
            )
            prepaid_amount += row.allocated_amount + tax_amount
        return prepaid_amount if prepaid_amount else 0.0

    @staticmethod
    def _get_currency(zatca_fields_dto: dict, doc: SalesInvoice) -> str:
        return doc.currency

    @staticmethod
    def _get_xml_tag(currency: str, prepaid_amount: float) -> XMLTag:
        return XMLTagFactory.create('PrepaidAmount', attributes={'currency': currency}, text=float(prepaid_amount))
