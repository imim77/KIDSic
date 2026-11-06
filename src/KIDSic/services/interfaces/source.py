from abc import ABC, abstractmethod


class SourceServiceInterface(ABC):
    @abstractmethod
    async def preview_sources(self) -> dict:
        """Validate metadata without opening a database connection."""

    @abstractmethod
    async def register_sources(self) -> dict:
        """Register selected JSON/CSV resources atomically; preserve flags and snapshots."""

    @abstractmethod
    async def preview_import(self) -> dict:
        """Download and normalize the resources without database writes."""

    @abstractmethod
    async def import_data(self, *, allow_removals: bool = False) -> dict:
        """Replace all selected sources atomically; reject missing keys by default."""
