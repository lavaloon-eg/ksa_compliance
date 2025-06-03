from dataclasses import dataclass
from typing import Optional
from ...validators import validate_mandatory_fields


@dataclass
class DocumentReference:
    """ZATCA-compliant document reference structure"""

    id: str
    issue_date: str
    document_type_code: str
    issue_time: Optional[str] = None

    def __post_init__(self):
        validate_mandatory_fields(
            self,
            {
                'id': 'Document Reference ID is mandatory',
                'issue_date': 'Issue date is mandatory',
                'issue_time': 'Issue time is mandatory',
                'document_type_code': 'Document type code is mandatory',
            },
        )
