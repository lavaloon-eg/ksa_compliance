from ...abs import BuilderAbc
from ...abs import ToDict


class _PrepaymentInvoiceLineBuilder(ToDict):
    def __init__(self, attributes):
        for key, value in attributes.items():
            setattr(self, key, value)


class PrepaymentInvoiceLineBuilder(BuilderAbc):
    mandatory_fields = [
        'id',
        'id_xml_tag',
        'invoice_quantity',
        'invoice_quantity_xml_tag',
        'line_extention_amount',
        'document_reference',
        'tax_total',
        'item',
        'price',
    ]

    def _validate(self):
        for field in self.mandatory_fields:
            if not hasattr(self, field):
                raise ValueError(f"Mandatory field '{field}' is missing in the prepayment invoice line.")

    def _create_returned_object(self):
        kwargs = self._get_non_callable_non_private_attributes(self)
        return _PrepaymentInvoiceLineBuilder(kwargs).to_dict()

    def set_id(self, id: str) -> 'PrepaymentInvoiceLineBuilder':
        self.id = id
        return self

    def set_id_xml_tag(self, id_xml_tag) -> 'PrepaymentInvoiceLineBuilder':
        self.id_xml_tag = id_xml_tag
        return self

    def set_uuid(self, uuid: str) -> 'PrepaymentInvoiceLineBuilder':
        self.uuid = uuid
        return self

    def set_invoice_quantity(self, invoice_quantity: float) -> 'PrepaymentInvoiceLineBuilder':
        self.invoice_quantity = invoice_quantity
        return self

    def set_invoice_quantity_xml_tag(self, invoice_quantity_xml_tag) -> 'PrepaymentInvoiceLineBuilder':
        self.invoice_quantity_xml_tag = invoice_quantity_xml_tag
        return self

    def set_line_extention_amount(self, line_extention_amount: float) -> 'PrepaymentInvoiceLineBuilder':
        self.line_extention_amount = line_extention_amount
        return self

    def set_line_extention_amount_xml_tag(self, line_extention_amount_xml_tag) -> 'PrepaymentInvoiceLineBuilder':
        self.line_extention_amount_xml_tag = line_extention_amount_xml_tag
        return self

    def set_document_reference(self, document_reference) -> 'PrepaymentInvoiceLineBuilder':
        self.document_reference = document_reference
        return self

    def set_tax_total(self, tax_total) -> 'PrepaymentInvoiceLineBuilder':
        self.tax_total = tax_total
        return self

    def set_item(self, item) -> 'PrepaymentInvoiceLineBuilder':
        self.item = item
        return self

    def set_price(self, price) -> 'PrepaymentInvoiceLineBuilder':
        self.price = price
        return self
