from abc import ABC, abstractmethod

from KIDSic.dto.ckan import CkanPackage, CkanResource


class CkanClientInterface(ABC):
    @abstractmethod
    async def get_package(self, dataset_id: str) -> CkanPackage:
        """Read package_show metadata; raise CkanError for upstream failures."""

    async def get_resources(self, dataset_id: str) -> list[CkanResource]:
        """Return resources unfiltered, as in FOIHireloom."""
        return (await self.get_package(dataset_id)).resources

    @abstractmethod
    async def download_records(self, resource: CkanResource) -> list[dict]:
        """Read bounded JSON or UTF-8 semicolon CSV; metadata is not a DataStore guarantee."""
