from abc import ABC


class Dictable:
    def to_dict(self):
        return Dictable._deep_dict_converter(self)
    @staticmethod
    def _deep_dict_converter(obj):
        pass

    @staticmethod
    def _get_non_callable_non_private_attributes(obj):
        lst = obj.items() if (type(obj) is dict) else obj.__dict__.items()
        return {k: v for k, v in lst if not k.startswith("__") and not callable(v)}


class ToDict:
    def to_dict(self):
        return {key: getattr(self, key) for key in vars(self) if not key.startswith('_')}

class PrepaymentInvoiceAbs(ABC):
    
    def validate_prepayment_invoice(self):
        """
        Validate the prepayment invoice.
        This method should be implemented by subclasses to include specific validation logic.
        """
        raise NotImplementedError("Subclasses must implement this method.")
    


class Factory(ABC):
    def create(self, zatca_additional_fields_dto):
        """
        Create a prepayment invoice from the given ZATCA additional fields DTO.
        This method should be implemented by subclasses to include specific creation logic.
        """
        raise NotImplementedError("Subclasses must implement this method.")
    

class BuilderAbc(ABC, Dictable):

    def _validate(self):
        pass


    def _create_returned_object(self):
        """
        Create and return the object based on the builder's state.
        This method should be implemented by subclasses to include specific creation logic.
        """
        raise NotImplementedError("Subclasses must implement this method.")
    
    def build(self):
        self._validate()
        return self._create_returned_object()