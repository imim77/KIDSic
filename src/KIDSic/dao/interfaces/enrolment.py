from abc import ABC, abstractmethod
from datetime import datetime
from KIDSic.dto.enrolment import EnrolmentDocument


class EnrolmentDocumentRepository(ABC):
    @abstractmethod
    async def import_document(self, document: EnrolmentDocument, snapshot_key: str,
                              fetched_at: datetime) -> dict:
        """Attach a reviewed document's excerpts to its institutions and activate it atomically."""
