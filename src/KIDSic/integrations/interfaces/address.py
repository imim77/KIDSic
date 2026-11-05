"""AddressLookup resolves explicit address text against sourced local records."""
from abc import ABC, abstractmethod


class AddressLookup(ABC):
    @abstractmethod
    def find(self, query: str) -> list[dict]:
        """Return exact or ambiguous local candidates; never estimate coordinates."""
