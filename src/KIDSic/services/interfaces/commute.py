"""Commute contracts separate the chat workflow from the journey ranking."""
from abc import ABC, abstractmethod
from collections.abc import Collection

from KIDSic.dto.commute import CommuteQuery
from KIDSic.dto.day_route import DayJourneyRequest
from KIDSic.dto.location import LocationFeature


class DayRouteServiceInterface(ABC):
    @abstractmethod
    async def find(self, text: str, city: str) -> list[LocationFeature]:
        """Return the routable facilities a kindergarten name or id means."""

    @abstractmethod
    async def recommend(self, request: DayJourneyRequest, facility_ids: Collection[str] | None = None) -> dict:
        """Rank routable facilities, or only facility_ids, by arrival at work."""


class CommuteServiceInterface(ABC):
    @abstractmethod
    async def recommend(self, query: CommuteQuery) -> dict:
        """Return ranked routes, or what the user must clarify first."""
