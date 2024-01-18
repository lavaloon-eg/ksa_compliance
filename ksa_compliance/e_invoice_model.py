from typing import Dict


ZATCA_DATA_TYPES = {bool, str, int, float, dict}


class InputModelAttribute:
    def __init__(self, attr_type: type, required: bool, min_len: int = None, max_len: int = None):
        self.attr_type = attr_type
        self.required = required
        self.min_len = min_len
        self.max_len = max_len


class MappingModel:
    _schema: Dict[str, "InputModelAttribute"] = {}
    error_dic = {}

    def __init__(self, **kwargs):
        self.data = kwargs.get("data")
        self.result = {}
        attrs = self.get_attributes()
        if attrs:
            self._schema = {}
            for key, value in attrs.items():
                self._schema.update({key: value})

        self.construct()

    def construct(self):
        for schema_key, schema_value in self._schema.items():
            field_required = schema_value.required
            min_len = schema_value.min_len or 0
            max_len = schema_value.max_len or 0
            field_name = schema_key

            if not self._validate_required(fieldname=field_name, required=field_required):
                continue

            _Type = schema_value.attr_type
            _field_value = self.data.get(field_name, None)
            res = None

            if field_required and _field_value is None:
                self.error_dic[field_name] = f"Missing field value: {field_name}."
                continue

            if _Type in ZATCA_DATA_TYPES:
                field_value_type = type(_field_value)

                if _Type == field_value_type:
                    res = field_value_type
                elif _Type is float and field_value_type is int:
                    res = float(field_value_type)
                else:
                    self.error_dic[field_name] = (f'Wrong type value for {field_name}: '
                                                  f'expected {_Type} and {field_value_type} is given')
                    continue

            if not min_len <= len(_field_value) <= max_len:
                self.error_dic[field_name] = f'Invalid {field_name} field size {len(_field_value)}'
                continue

            setattr(self, schema_key, res)
            self.result[field_name] = _field_value

    def _validate_required(self, fieldname: str, required: bool) -> bool:
        if fieldname not in self.data and required:
            self.error_dic[fieldname] = f'Missing required field: {fieldname}'
            return False
        return True

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

        if _Type.__base__ == object:
            return res
        return MappingModel._get_attributes(_Type.__base__, res)
