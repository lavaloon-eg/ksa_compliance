from ...abs import BuilderAbc
from ...xml_tag import XMLTag
from ...abs import ToDict

class _PrepaymenInvoiceBuilder(ToDict):
    def __init__(self, attributes):
        for key, value in attributes.items():
            setattr(self, key, value)


class PrepaymentInvoiceBuilder(BuilderAbc):
    mandatory_fields = [
        "prepaid_amount",
        "currency",
        "invoice_lines",
        "prepaid_amount_xml_tag",
    ]

    def _validate(self):
        for field in self.mandatory_fields:
            if not hasattr(self, field):
                raise ValueError(f"Mandatory field '{field}' is missing in the prepayment invoice.")
            
    def _create_returned_object(self):
        kwargs = self._get_non_callable_non_private_attributes(self)
        return _PrepaymenInvoiceBuilder(kwargs).to_dict()
    
    def set_prepaid_amount(self, prepaid_amount:float)-> "PrepaymentInvoiceBuilder":
        self.prepaid_amount = prepaid_amount
        return self
    
    def set_currency(self, currency:str)-> "PrepaymentInvoiceBuilder":
        self.currency = currency
        return self
    
    def set_prepaid_amount_xml_tag(self, prepaid_amount_xml_tag:XMLTag)-> "PrepaymentInvoiceBuilder":
        self.prepaid_amount_xml_tag = prepaid_amount_xml_tag
        return self
    
    def set_invoice_lines(self, invoice_lines:list)-> "PrepaymentInvoiceBuilder":
        self.invoice_lines = invoice_lines
        return self

    
    

