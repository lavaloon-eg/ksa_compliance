# import frappe
from ksa_compliance.output_models.e_invoice_model import MappingModel, InputModelAttribute


class BusinessSettingsOutputModel(MappingModel):
    # Any parameter won't be passed to InputModelAttribute it will be assigned with its default value
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _get_list(self, attribute_name: str, raw_value: list) -> tuple:
        """
        Override _get_list method to exclude dict from nested lists condition
        """
        res = []
        for it in raw_value:
            _value = None
            if self._is_iterable_type(type(it), attribute_name, it):
                return f"Can't have nested lists or tuples, not supported.", res
            else:
                _value = it

            if _value:
                res.append(_value)

        return None, res

    # TODO: Complete the implementation
    def validate_scheme_with_order(self, additional_ids, valid_scheme_ids, source_property):
        if isinstance(additional_ids, dict):
            rem_scheme_ids = valid_scheme_ids

            for scheme_id, scheme_value in additional_ids.items():
                if scheme_id not in valid_scheme_ids:
                    self.error_dic['party_identification'] = f"Invalid scheme ID: {scheme_id} for Seller Additional IDs"
                    return False
                elif scheme_id not in rem_scheme_ids:
                    self.error_dic['party_identification'] = (f"Invalid scheme ID Order: "
                                                              f"for {additional_ids} in {source_property} Additional IDs")
                    return False
                else:
                    index = rem_scheme_ids.index(scheme_id)
                    rem_scheme_ids = rem_scheme_ids[index:]
            return True
        else:
            self.error_dic['party_identification'] = "Invalid data type, expecting a list of tuples"
            return False

    # party_identification is a list of seller IDs
    party_identification = InputModelAttribute(attr_type=list, required=True, list_of=tuple)
    street_name = InputModelAttribute(attr_type=str, required=True)
    building_number = InputModelAttribute(attr_type=str, required=True)
    city_name = InputModelAttribute(attr_type=str, required=True, max_len=127)
    postal_code = InputModelAttribute(attr_type=str, required=True)
    city_subdivision_name = InputModelAttribute(attr_type=str, required=True, min_len=1, max_len=127)  # district
    identification_code = InputModelAttribute(attr_type=str, required=True)  # country_code
    company_id = InputModelAttribute(attr_type=str, required=False)  # VAT registration number
    registration_name = InputModelAttribute(attr_type=str, required=False, min_len=1)  # Seller name

