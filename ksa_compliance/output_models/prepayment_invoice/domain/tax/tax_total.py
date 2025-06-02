from ...abs import BuilderAbc
from ...abs import ToDict


class _TaxTotalBuilder(ToDict):
    def __init__(self, attributes):
        for key, value in attributes.items():
            setattr(self, key, value)


class TaxTotalBuilder(BuilderAbc):
    mandatory_fields = []

    def _validate(self):
        for field in self.mandatory_fields:
            if not hasattr(self, field):
                raise ValueError(f"Mandatory field '{field}' is missing in the tax total.")

    def _create_returned_object(self):
        kwargs = self._get_non_callable_non_private_attributes(self)
        return _TaxTotalBuilder(kwargs).to_dict()

    def set_tax_amount(self, tax_amount: float) -> 'TaxTotalBuilder':
        self.tax_amount = tax_amount
        return self

    def set_rounding_amount(self, rounding_amount: float) -> 'TaxTotalBuilder':
        self.rounding_amount = rounding_amount
        return self

    def set_tax_subtotal(self, tax_sub_total) -> 'TaxTotalBuilder':
        self.tax_sub_total = tax_sub_total
        return self

    def set_tax_sub_total(self, tax_sub_total: float) -> 'TaxTotalBuilder':
        self.tax_sub_total = tax_sub_total
        return self
