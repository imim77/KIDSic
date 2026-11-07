from abc import ABC, abstractmethod
from KIDSic.dto.rag import RagContext, RagQuery


class RagServiceInterface(ABC):
    @abstractmethod
    async def retrieve(self, query: RagQuery) -> RagContext:
        """Retrieve attributed evidence within the explicitly selected kindergarten."""


class EvidenceBuilder(ABC):
    @abstractmethod
    def feature_id(self, row) -> str:
        """Return the map feature id a location row is shown under."""

    @abstractmethod
    def context_scope(self, rows) -> dict:
        """Return the location and kindergarten ids to search documents for."""

    @abstractmethod
    def collect(self, rows, chunks) -> list:
        """Return deduplicated evidence for the rows and matching documents."""
