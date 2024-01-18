class MappingModel:
    def __init__(self, mapping_dict=None):
        # Constructor implementation for MappingModel
        if mapping_dict is not None:
            # Process the mapping_dict as needed
            print(f"MappingModel initialized with mapping_dict: {mapping_dict}")


class BusinessSettingsInputModel(MappingModel):
    def __init__(self, business_settings_dict=None, mapping_dict=None):
        # Pass mapping_dict to the constructor of the superclass (MappingModel)
        super().__init__(mapping_dict)

        # Constructor implementation for BusinessSettingsInputModel
        if business_settings_dict is not None:
            # Process the business_settings_dict as needed
            print(f"BusinessSettingsInputModel initialized with business_settings_dict: {business_settings_dict}")

    @classmethod
    def initialize_with_example(cls):
        # Example usage to initialize BusinessSettingsInputModel with example data
        business_settings_data = {"key1": "value1", "key2": "value2"}
        mapping_data = {"mapping_key": "mapping_value"}
        return cls(business_settings_dict=business_settings_data, mapping_dict=mapping_data)


# Example usage:
business_settings_instance = BusinessSettingsInputModel.initialize_with_example()
