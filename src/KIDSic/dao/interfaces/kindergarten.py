"""Persistence contract for source-grounded document retrieval."""
from abc import ABC, abstractmethod


class KindergartenRepository(ABC):
    @abstractmethod
    async def retrieve_context(self, *, location_ids, kindergarten_ids=(), limit=30):
        """Retrieve accepted documents only within the supplied candidate scope."""
