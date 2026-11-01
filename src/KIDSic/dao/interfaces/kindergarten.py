"""Persistence contract; implementations do not own transactions."""
from abc import ABC, abstractmethod


class KindergartenRepository(ABC):
    @abstractmethod
    async def list_cities(self):
        """Return canonical city keys and curated aliases."""

    @abstractmethod
    async def find_options(self, *, city, age_months, as_of=None, include_unknown=False, limit=50):
        """Return age-appropriate options and optionally unknown age conditions."""
