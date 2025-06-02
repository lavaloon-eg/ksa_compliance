from abc import ABC


class ToDict:
    def to_dict(self):
        return {key: getattr(self, key) for key in vars(self) if not key.startswith('_')}


class PrepaymentInvoiceAbs(ABC):
    def validate_prepayment_invoice(self):
        """
        Validate the prepayment invoice.
        This method should be implemented by subclasses to include specific validation logic.
        """
        raise NotImplementedError('Subclasses must implement this method.')


class Factory(ABC):
    def create(self, zatca_additional_fields_dto):
        """
        Create a prepayment invoice from the given ZATCA additional fields DTO.
        This method should be implemented by subclasses to include specific creation logic.
        """
        raise NotImplementedError('Subclasses must implement this method.')


class BuilderAbc(ABC):
    def _validate(self):
        pass

    def _create_returned_object(self):
        """
        Create and return the object based on the builder's state.
        This method should be implemented by subclasses to include specific creation logic.
        """
        raise NotImplementedError('Subclasses must implement this method.')

    def build(self):
        self._validate()
        return self._create_returned_object()
