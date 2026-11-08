"""HistoricalTableParser preserves source granularity and excludes published totals."""
import re
from collections import Counter
from collections.abc import Mapping

from KIDSic.dto.historical import HistoricalRow, HistoricalSourceDefinition
from KIDSic.exceptions import SourceImportError
from KIDSic.services.interfaces.historical import HistoricalRowParser, HistoricalTableLayout


class HistoricalTableParser(HistoricalRowParser):
    """HistoricalTableParser applies the definition's layout, then refuses a
    snapshot whose stated date or record identities do not hold."""
    def __init__(self, layouts: Mapping[str, HistoricalTableLayout]):
        self._layouts = dict(layouts)

    def parse(self, table: list[list[str]], definition: HistoricalSourceDefinition) -> tuple[HistoricalRow, ...]:
        if not table:
            raise SourceImportError('Historical table is empty.')
        parser = definition.source.parser
        layout = self._layouts.get(parser)
        if layout is None:
            raise SourceImportError(f'Unknown historical parser: {parser}.')
        if layout.dated:
            self._check_date(table, definition)
        rows = layout.parse(table)
        duplicates = [key for key, count in Counter(r.source_key for r in rows).items() if count > 1]
        if not rows or duplicates:
            raise SourceImportError('Historical table has no records or duplicate identities.')
        return tuple(rows)

    @staticmethod
    def _check_date(table, definition):
        dates = re.findall(r'STANJE NA DAN\s+(\d+)\.(\d+)\.(\d{4})\.',
                           ' '.join(cell for row in table for cell in row), re.I)
        expected = definition.reference_date
        if dates != [(str(expected.day), str(expected.month), str(expected.year))]:
            raise SourceImportError('Historical observation date does not match the configured snapshot.')
