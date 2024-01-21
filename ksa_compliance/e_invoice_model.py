from typing import Dict, Optional

ZATCA_DATA_TYPES = {bool, str, int, float, dict}


class ZATCAException(Exception):
    pass


class MappingModel:
    _schema: Dict[str, "InputModelAttribute"] = {}

    def __init__(self, **kwargs):
        self.data = kwargs.get("data")
        self.result = {}
        self.error_dic = {}
        attrs = self.get_attributes()
        if attrs:
            self._schema = {}
            for key, value in attrs.items():
                self._schema.update({key: value})

        self.construct()

    def construct(self):
        for schema_key, schema_value in self._schema.items():
            field_required = schema_value.required
            min_len = schema_value.min_len
            max_len = schema_value.max_len
            field_name = schema_key

            valid, error = self._validate_required(fieldname=field_name, required=field_required)
            if not valid:
                self.error_dic[field_name] = error
                continue

            _Type = schema_value.attr_type
            _field_value = self.data.get(field_name, None)
            res = _field_value

            if field_required and _field_value is None:
                self.error_dic[field_name] = f"Missing field value: {field_name}."
                continue

            if _Type in ZATCA_DATA_TYPES:
                field_value_type = type(_field_value)

                if _Type == field_value_type:
                    res = _field_value
                elif _Type is float and field_value_type is int:
                    res = float(_field_value)
                else:
                    self.error_dic[field_name] = (f'Wrong type value for {field_name}: '
                                                  f'expected {_Type} and {field_value_type} is given')
                    continue
            elif self._is_iterable_type(_Type, field_name, _field_value):
                _List_of = schema_value.list_of
                error, res = self._get_list(field_name, _field_value)
                if error:
                    self.error_dic[field_name] = error
                    continue
            else:
                self.error_dic[field_name] = f"{_Type} is an invalid data type."
                continue

            if not min_len <= len(_field_value) <= max_len:
                self.error_dic[field_name] = f'Invalid {field_name} field size {len(_field_value)}'
                continue

            setattr(self, schema_key, res)
            self.result[field_name] = res

    def _validate_required(self, fieldname: str, required: bool) -> tuple:
        if fieldname not in self.data and required:
            return False, f'Missing required field: {fieldname}'
        return True, None

    def _is_iterable_type(self, expected_type: type, attribute_name: str, raw_value: any) -> bool:
        """
        Check the field type and value type if the field is iterable or not
        """
        iterable_types = {list, tuple}
        if expected_type in iterable_types:
            if type(raw_value) in iterable_types:
                return True
            self.error_dic[attribute_name] = (
                f"Expected type {expected_type} for attribute name {attribute_name}, mismatch sent value {raw_value}")
        return False

    def _get_list(self, attribute_name: str, raw_value: list) -> tuple:
        res = []
        for it in raw_value:
            _value = None
            if self._is_iterable_type(type(it), attribute_name, it) or isinstance(it, dict):
                return f"Can't have nested lists or tuples or dict, not supported.", res
            else:
                _value = it

            if _value:
                res.append(_value)

        return None, res

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


class InputModelAttribute:
    def __init__(self, attr_type: type, required: bool, list_of: Optional[type] = None, min_len: int = 0,
                 max_len: int = 1000):
        self.attr_type = attr_type
        self.required = required
        self.list_of = list_of
        self.min_len = min_len
        self.max_len = max_len

        if self.attr_type == list and not self.list_of:
            raise ZATCAException("list_of attribute can't be empty with list attr_type")
