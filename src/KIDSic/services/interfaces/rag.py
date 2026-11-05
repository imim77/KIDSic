from abc import ABC, abstractmethod
from KIDSic.dto.rag import RagContext, RagQuery


class RagServiceInterface(ABC):
    @abstractmethod
    async def retrieve(self, query: RagQuery) -> RagContext:
        """Retrieve attributed evidence within the explicitly selected kindergarten."""
