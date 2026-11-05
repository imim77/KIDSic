"""JourneyPlanner supplies timetable-aware journeys without coupling policy to HTTP."""
from abc import ABC, abstractmethod
from datetime import datetime

from KIDSic.dto.day_route import DayPoint, Journey


class RoutingUnavailable(RuntimeError):
    pass


class JourneyPlanner(ABC):
    @abstractmethod
    async def plan(self, origin: DayPoint, destination: DayPoint,
                   departure: datetime, mode: str) -> Journey | None:
        """Return the earliest arrival among the router's alternatives, or no route."""
