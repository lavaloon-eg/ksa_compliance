from ...abs import BuilderAbc
from ...abs import ToDict


class _TaxSubtotalBuilder(ToDict):
    def __init__(self, attributes):
        for key, value in attributes.items():
            setattr(self, key, value)


class TaxSubtotalBuilder(BuilderAbc):
    mandatory_fields = [
        'taxable_amount',
        'tax_amount',
        'tax_category_id',
    ]

    def _validate(self):
        for field in self.mandatory_fields:
            if not hasattr(self, field):
                raise ValueError(f"Mandatory field '{field}' is missing in the tax subtotal.")

    def _create_returned_object(self):
        kwargs = self._get_non_callable_non_private_attributes(self)
        return _TaxSubtotalBuilder(kwargs).to_dict()

    def set_taxable_amount(self, taxable_amount: float) -> 'TaxSubtotalBuilder':
        self.taxable_amount = taxable_amount
        return self

    def set_tax_amount(self, tax_amount: float) -> 'TaxSubtotalBuilder':
        self.tax_amount = tax_amount
        return self

    def set_tax_category_id(self, tax_category_id: str) -> 'TaxSubtotalBuilder':
        self.tax_category_id = tax_category_id
        return self

    def set_tax_percent(self, tax_percent: float) -> 'TaxSubtotalBuilder':
        self.tax_percent = tax_percent
        return self

    def set_tax_scheme(self, tax_scheme) -> 'TaxSubtotalBuilder':
        self.tax_scheme = tax_scheme
        return self
