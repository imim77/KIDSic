from abc import ABC, abstractmethod

from KIDSic.dto.location import LocationCollection, LocationQuery


class LocationServiceInterface(ABC):
    @abstractmethod
    async def list_locations(self, query: LocationQuery) -> LocationCollection:
        """Return complete GeoJSON with explicit coordinate coverage."""
