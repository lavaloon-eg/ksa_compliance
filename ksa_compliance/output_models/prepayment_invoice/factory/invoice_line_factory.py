import frappe

from ..abs import Factory
from ..factory.xml_factory import XMLTagFactory
from ..xml_tag import XMLTag
from ..domain.prepayment_invoice_line.prepayment_invoice_line import PrepaymentInvoiceLineBuilder
from ..domain.document_reference.document_reference import DocumentReferenceBuilder
from ..domain.tax.tax_total import TaxTotalBuilder
from ..domain.tax.tax_subtotal import TaxSubtotalBuilder
from ..domain.item.item import ItemBuilder
from ksa_compliance.standard_doctypes.tax_category import map_tax_category


class InvoiceLineFactory(Factory):
    @staticmethod
    def create(zatca_fields_dto: dict, doc):
        """
        Create invoice lines based on the ZATCA fields DTO and the document type.
        """
        invoice_lines = [InvoiceLineFactory._create_prepayment_invoice_line(advance, doc) for advance in doc.advances]
        return invoice_lines

    @staticmethod
    def _create_prepayment_invoice_line(advance, doc):
        prepayment_invoice_line_builder = PrepaymentInvoiceLineBuilder()
        document_reference = frappe.get_cached_doc(advance.reference_type, advance.reference_name)

        currency = doc.currency if hasattr(doc, 'currency') else 'SAR'
        uuid = InvoiceLineFactory._get_uuid(advance, doc, document_reference)

        prepayment_invoice_line_builder.set_id(advance.idx + len(doc.items)).set_id_xml_tag(
            InvoiceLineFactory._get_idx_xml_tag(advance.idx)
        ).set_invoice_quantity(0.0).set_invoice_quantity_xml_tag(
            InvoiceLineFactory._get_invoice_quantity_xml_tag(0.0, currency)
        ).set_line_extention_amount(0.0).set_line_extention_amount_xml_tag(
            InvoiceLineFactory._get_line_extention_amount_xml_tag(0.0, currency)
        ).set_uuid(uuid)

        prepayment_invoice_line_builder.set_document_reference(
            InvoiceLineFactory._get_document_reference(advance, doc, document_reference)
        )
        prepayment_invoice_line_builder.set_tax_total(
            InvoiceLineFactory._get_tax_total(advance, doc, document_reference)
        )
        prepayment_invoice_line_builder.set_item(InvoiceLineFactory._get_item(advance, doc, document_reference))
        prepayment_invoice_line_builder.set_price(InvoiceLineFactory._get_price(advance, doc, document_reference))
        return prepayment_invoice_line_builder.build()

    @staticmethod
    def _get_idx_xml_tag(idx: int) -> XMLTag:
        return XMLTagFactory.create('ID', attributes=None, text=str(idx))

    @staticmethod
    def _get_invoice_quantity_xml_tag(invoice_quantity: float, currency: str) -> XMLTag:
        return XMLTagFactory.create('InvoiceQuantity', attributes={'unitCode': currency}, text=float(invoice_quantity))

    @staticmethod
    def _get_line_extention_amount_xml_tag(line_extention_amount: float, currency: str) -> XMLTag:
        return XMLTagFactory.create(
            'LineExtensionAmount', attributes={'currencyID': currency}, text=float(line_extention_amount)
        )

    @staticmethod
    def _get_uuid(advance, doc, document_reference):
        uuid = frappe.db.get_value(
            'Sales Invoice Additional Fields',
            {'invoice_doctype': document_reference.doctype, 'sales_invoice': document_reference.name},
            'uuid',
        )
        return uuid

    @staticmethod
    def _get_document_reference(advance, doc, document_reference):
        document_reference_builder = DocumentReferenceBuilder()
        document_reference_builder.set_id(advance.reference_name).set_issue_date(
            document_reference.posting_date.strftime('%Y-%m-%d')
        ).set_issue_time(
            InvoiceLineFactory._get_issude_time(document_reference.custom_posting_time)
        ).set_document_type_code(386)
        return document_reference_builder.build()

    @staticmethod
    def _get_issude_time(posting_date):
        # For timedelta (duration) formatting
        time_delta = posting_date  # timedelta object

        total_seconds = time_delta.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        formatted_time = f'{hours:02d}:{minutes:02d}:{seconds:02d}'
        return formatted_time

    @staticmethod
    def _get_tax_total(advance, doc, document_reference):
        tax_percent = frappe.db.get_value(
            'Sales Taxes and Charges',
            {
                'parent': document_reference.sales_taxes_and_charges_template,
                'parenttype': 'Sales Taxes and Charges Template',
            },
            ['rate'],
        )
        tax_id = frappe.db.get_value(
            'Sales Taxes and Charges Template', document_reference.sales_taxes_and_charges_template, 'tax_category'
        )

        tax_category_id = map_tax_category(tax_category_id=tax_id)

        tax_total = TaxTotalBuilder()
        tax_total.set_tax_amount(0.0).set_rounding_amount(0.0).set_tax_subtotal(
            InvoiceLineFactory._get_tax_subtotal(advance, doc, tax_percent, tax_category_id)
        )
        return tax_total.build()

    @staticmethod
    def _get_tax_subtotal(advance, doc, tax_percent, tax_category_id):
        tax_subtotal = TaxSubtotalBuilder()
        tax_subtotal.set_taxable_amount(advance.allocated_amount).set_tax_amount(
            advance.allocated_amount * (tax_percent / 100)
        ).set_tax_category_id(tax_category_id.tax_category_code).set_tax_percent(tax_percent).set_tax_scheme('VAT')
        return tax_subtotal.build()

    @staticmethod
    def _get_item(advance, doc, document_reference):
        tax_percent = frappe.db.get_value(
            'Sales Taxes and Charges',
            {
                'parent': document_reference.sales_taxes_and_charges_template,
                'parenttype': 'Sales Taxes and Charges Template',
            },
            ['rate'],
        )
        tax_id = frappe.db.get_value(
            'Sales Taxes and Charges Template', document_reference.sales_taxes_and_charges_template, 'tax_category'
        )
        tax_category_id = map_tax_category(tax_category_id=tax_id)
        item = ItemBuilder()
        item.set_name(document_reference.custom_prepayment_invoice_description).set_item_tax_category(
            tax_category_id.tax_category_code
        ).set_item_tax_percent(tax_percent).set_item_tax_scheme('VAT')
        return item.build()

    @staticmethod
    def _get_price(advance, doc, document_reference):
        return 0.0
