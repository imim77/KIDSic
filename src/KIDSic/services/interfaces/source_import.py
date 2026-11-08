"""Source import contracts let a service plan and normalize resources
without knowing which catalogue rules or schemas apply."""
from abc import ABC, abstractmethod

from KIDSic.dto.ckan import CkanPackage
from KIDSic.dto.source import KindergartenRow, PlannedSource, SourceDefinition


class SourcePlanner(ABC):
    @abstractmethod
    def select(self, definition: SourceDefinition, package: CkanPackage) -> PlannedSource:
        """Return the one resource the definition identifies in the package."""

    @abstractmethod
    def validate(self, sources: list[PlannedSource]) -> None:
        """Raise when the selected sources overlap or are empty."""


class RecordNormalizer(ABC):
    @abstractmethod
    def normalize(self, records: list[dict], parser: str) -> tuple[KindergartenRow, ...]:
        """Return the records as rows using the named schema."""
