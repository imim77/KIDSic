"""Persistence contract; implementations do not own transactions."""
from abc import ABC, abstractmethod


class KindergartenRepository(ABC):
    @abstractmethod
    async def list_cities(self):
        """Return settlement and municipality keys with curated aliases."""

    @abstractmethod
    async def find_options(self, *, city, age_months, as_of=None, include_unknown=False, limit=50):
        """Return age-appropriate options and optionally unknown age conditions."""

    @abstractmethod
    async def retrieve_context(self, *, location_ids, text='', embedding=None,
                               embedding_model=None, program_ids=(), kindergarten_ids=(), limit=8):
        """Retrieve source-grounded chunks only within the supplied candidate scope."""
