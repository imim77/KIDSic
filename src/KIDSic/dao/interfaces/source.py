from abc import ABC, abstractmethod

from KIDSic.dto.source import PlannedSource, SourceSnapshot


class SourceRepository(ABC):
    @abstractmethod
    async def register(self, source: PlannedSource) -> str:
        """Upsert metadata; return added/updated/unchanged, preserving approval/history."""

    @abstractmethod
    async def import_snapshot(self, snapshot: SourceSnapshot) -> dict:
        """Store rows and activate their batch together in the caller's transaction."""
