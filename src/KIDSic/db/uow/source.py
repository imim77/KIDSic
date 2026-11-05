"""Separate write Unit of Work; search keeps its read-only snapshot contract."""
from abc import ABC, abstractmethod
from collections.abc import Callable

from KIDSic.dao.interfaces.source import SourceRepository
from KIDSic.dao.interfaces.historical import HistoricalRepository
from KIDSic.dao.interfaces.enrolment import EnrolmentDocumentRepository


class SourceUnitOfWork(ABC):
    sources: SourceRepository
    historical: HistoricalRepository
    enrolment: EnrolmentDocumentRepository

    @abstractmethod
    async def __aenter__(self):
        """Open the import transaction."""

    @abstractmethod
    async def __aexit__(self, exc_type, exc, traceback):
        """Commit on success, otherwise roll back."""




type SourceUnitOfWorkFactory = Callable[[], SourceUnitOfWork]
