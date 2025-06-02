from ...abs import BuilderAbc
from ...abs import ToDict


class _ItemBuilder(ToDict):
    def __init__(self, attributes):
        for key, value in attributes.items():
            setattr(self, key, value)

class ItemBuilder(BuilderAbc):
    mandatory_fields = [

    ]

    def _validate(self):
        for field in self.mandatory_fields:
            if not hasattr(self, field):
                raise ValueError(f"Mandatory field '{field}' is missing in the item.")

    def _create_returned_object(self):
        kwargs = self._get_non_callable_non_private_attributes(self)
        return _ItemBuilder(kwargs).to_dict()

    def set_name(self, name: str) -> "ItemBuilder":
        self.name = name
        return self
    def set_item_tax_category(self, item_tax_category) -> "ItemBuilder":
        self.item_tax_category = item_tax_category
        return self
    def set_item_tax_percent(self, item_tax_percent: float) -> "ItemBuilder":
        self.item_tax_percent = item_tax_percent
        return self
    def set_item_tax_scheme(self, item_tax_scheme) -> "ItemBuilder":
        self.item_tax_scheme = item_tax_scheme
        return self