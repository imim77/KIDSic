"""Historical parsing contracts let a new published table layout be added
without changing the parser that checks dates and identities."""
from abc import ABC, abstractmethod

from KIDSic.dto.historical import HistoricalRow, HistoricalSourceDefinition


class HistoricalTableLayout(ABC):
    """HistoricalTableLayout reads one published table layout into rows."""
    dated = False

    @abstractmethod
    def parse(self, table: list[list[str]]) -> list[HistoricalRow]:
        """Return the table's records, excluding published totals."""


class HistoricalRowParser(ABC):
    @abstractmethod
    def parse(self, table: list[list[str]], definition: HistoricalSourceDefinition) -> tuple[HistoricalRow, ...]:
        """Return validated rows for the definition's configured layout."""
