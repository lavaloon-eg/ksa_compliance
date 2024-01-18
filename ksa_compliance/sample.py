import datetime
from datetime import date
from typing import Dict, Optional


PRIMITIVE_TYPES = {bool, str, int, float, None, datetime, date, dict, list}


class InputModelAttribute:
    def __init__(self, attr_type: type, required: bool):
        self.attr_type = attr_type
        self.required = required


class InputModel:
    _schema: Dict[str, "InputModelAttribute"] = {}

    def __init__(self, **kwargs):
        self.data = kwargs.get("bs")
        attrs = self.get_attributes()
        if attrs:
            self._schema = {}
            for key, value in attrs.items():
                self._schema.update({key: value})

        self.construct()

    def construct(self):
        for schema_key, schema_value in self._schema.items():
            attribute_required = schema_value.required
            field_name = schema_key  # Field Name

            self._validate_required(schema_attribute=field_name, required=attribute_required)

            _Type = schema_value.attr_type
            _raw_data_value = self.data.get(field_name, None)
            res = None

            if attribute_required and _raw_data_value is None:
                raise Exception(f"Required attribute {schema_key} cannot be null")

            if _Type in PRIMITIVE_TYPES:
                raw_type = type(_raw_data_value)

                if _Type == raw_type:
                    res = _raw_data_value
                elif self._convert_primitive_type(_raw_data_value, raw_type, _Type):  # Parsing
                    res = self._convert_primitive_type(_raw_data_value, raw_type, _Type)
                else:
                    raise Exception(
                        f"Expected type {_Type} for attribute name {schema_key}, mismatch sent value {_raw_data_value}")
            else:
                raise Exception(f"{_Type} is an invalid data type.")

            setattr(self, schema_key, res)

    def _convert_primitive_type(self, value: any, from_type: type, to_type: type) -> Optional[any]:
        return float(value) if from_type == int and to_type == float else None

    def _validate_required(self, schema_attribute: str, required: bool) -> None:
        if schema_attribute not in self.data and required:
            raise Exception(f"{schema_attribute} argument is missing.")

    def get_attributes(self) -> Dict:
        return self._get_attributes(type(self))

    @staticmethod
    def _get_attributes(_Type: type, res=None):
        """
            Recursive method, to support models inheritance.
            The method gets the attributes of the child type then recurse to its parents to fetch their attributes too.
        """

        if res is None:
            res = {}

        res.update({key: value for key, value in _Type.__dict__.items() if
                    issubclass(type(value), InputModelAttribute) and key not in res})
        print(_Type.__base__)
        if _Type.__base__ == object:
            return res
        return InputModel._get_attributes(_Type.__base__, res)


class BusinessSettings(InputModel):
    party_identification = InputModelAttribute(attr_type=str, required=True)
    street_number = InputModelAttribute(attr_type=str, required=False)


business_settings = {"party_identification": "party1", "street_number": "street1"}

result = BusinessSettings(bs=business_settings)

print(result.data)
