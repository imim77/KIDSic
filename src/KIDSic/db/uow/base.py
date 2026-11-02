"""A request-scoped read snapshot shared by all repository calls."""
from abc import ABC, abstractmethod
from KIDSic.dao.interfaces.kindergarten import KindergartenRepository
from KIDSic.dao.interfaces.location import LocationRepository


class UnitOfWork(ABC):
    search: KindergartenRepository
    locations: LocationRepository

    @abstractmethod
    async def __aenter__(self):
        """Acquire a snapshot and its repositories."""

    @abstractmethod
    async def __aexit__(self, exc_type, exc, traceback):
        """Finish the transaction and release resources."""
