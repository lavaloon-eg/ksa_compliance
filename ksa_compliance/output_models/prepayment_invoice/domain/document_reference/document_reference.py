from ...abs import BuilderAbc
from ...abs import ToDict

class _DocumentReferenceBuilder(ToDict):
    def __init__(self, attributes):
        for key, value in attributes.items():
            setattr(self, key, value)

class DocumentReferenceBuilder(BuilderAbc):
    mandatory_fields = [
        "id",
        "document_type_code",
        "issue_date",
    ]
    def _validate(self):
        for field in self.mandatory_fields:
            if not hasattr(self, field):
                raise ValueError(f"Mandatory field '{field}' is missing in the document reference.")
    def _create_returned_object(self):
        kwargs = self._get_non_callable_non_private_attributes(self)
        return _DocumentReferenceBuilder(kwargs).to_dict()
    
    def set_id(self, id: str) -> "DocumentReferenceBuilder":
        self.id = id
        return self
    
    def set_issue_date(self, issue_date: str) -> "DocumentReferenceBuilder":
        self.issue_date = issue_date
        return self
    def set_issue_time(self, issue_time: str) -> "DocumentReferenceBuilder":
        self.issue_time = issue_time
        return self
    
    def set_document_type_code(self, document_type_code: str) -> "DocumentReferenceBuilder":
        self.document_type_code = document_type_code
        return self

