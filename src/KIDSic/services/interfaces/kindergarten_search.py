from abc import ABC, abstractmethod
from KIDSic.dto.search import Recommendation


class KindergartenSearchServiceInterface(ABC):
    @abstractmethod
    async def recommend(self, question: str, *, as_of=None) -> Recommendation:
        """Return confirmed candidates, unknown conditions and source evidence."""
