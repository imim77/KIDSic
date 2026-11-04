from abc import ABC, abstractmethod
from KIDSic.dto.historical import HistoricalSnapshot


class HistoricalRepository(ABC):
    @abstractmethod
    async def import_snapshot(self, snapshot: HistoricalSnapshot) -> dict:
        """Link a historical batch to existing objects and activate it atomically."""
