"""SourceRecordNormalizer applies an injected schema while guarding snapshot identity."""
from collections.abc import Mapping
from KIDSic.dto.source import KindergartenRow
from KIDSic.dto.municipality import MUNICIPALITIES
from KIDSic.exceptions import SourceImportError
from KIDSic.services.interfaces.source_parser import SourceRowParser


class SourceRecordNormalizer:
    def __init__(self, parsers: Mapping[str, SourceRowParser]):
        self._parsers = dict(parsers)

    def normalize(self, records: list[dict], parser: str) -> tuple[KindergartenRow, ...]:
        if not records:
            raise SourceImportError('Empty resource refused; the last successful snapshot is preserved.')
        try:
            adapter = self._parsers[parser]
        except KeyError:
            raise SourceImportError(f'{parser} row 1: Unknown parser: {parser}.') from None
        rows, keys = [], set()
        for ordinal, record in enumerate(records, start=1):
            try:
                row = adapter.parse(record)
                if row is None or row.municipality not in MUNICIPALITIES:
                    continue
                if row.source_key in keys:
                    raise SourceImportError('Duplicate row identity in resource.')
                keys.add(row.source_key)
                rows.append(row)
            except SourceImportError as error:
                raise SourceImportError(f'{parser} row {ordinal}: {error}') from error
        return tuple(rows)
