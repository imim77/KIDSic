from abc import ABC, abstractmethod

from KIDSic.dto.source import PlannedSource, SourceSnapshot


class SourceRepository(ABC):
    @abstractmethod
    async def register(self, source: PlannedSource) -> str:
        """Upsert metadata; return added/updated/unchanged, preserving approval/history."""

    @abstractmethod
    async def import_snapshot(self, snapshot: SourceSnapshot, *, allow_removals: bool = False) -> dict:
        """Replace state atomically; missing keys require explicit removal permission."""
