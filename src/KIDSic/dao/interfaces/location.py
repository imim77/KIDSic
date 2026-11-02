"""LocationRepository supplies complete location rows without owning transactions."""
from abc import ABC, abstractmethod

from KIDSic.dto.location import LocationQuery


class LocationRepository(ABC):
    @abstractmethod
    async def list_locations(self, query: LocationQuery):
        """Return active facilities and explicit seat fallbacks matching filters."""
