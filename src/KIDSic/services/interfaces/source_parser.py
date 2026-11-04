"""SourceRowParser defines one source schema without network or database access."""
from abc import ABC, abstractmethod
from KIDSic.dto.source import KindergartenRow


class SourceRowParser(ABC):
    @abstractmethod
    def parse(self, record: dict) -> KindergartenRow | None:
        """Return a normalized row, or None for an explicitly excluded record."""
