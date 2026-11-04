"""HistoricalService validates all downloads before opening the write transaction."""
from datetime import datetime, timezone
from collections.abc import Mapping, Sequence

from KIDSic.integrations.interfaces.ckan import CkanClientInterface
from KIDSic.db.uow.source import SourceUnitOfWorkFactory
from KIDSic.dto.historical import HistoricalSnapshot, HistoricalSourceDefinition
from KIDSic.services.concrete.historical_parser import HistoricalTableParser
from KIDSic.services.concrete.source_planner import SourceRegistrationPlanner
from KIDSic.exceptions import SourceImportError


class HistoricalService:
    def __init__(self, clients: Mapping[str, CkanClientInterface],
                 definitions: Sequence[HistoricalSourceDefinition],
                 uow_factory: SourceUnitOfWorkFactory | None = None, *,
                 parser: HistoricalTableParser | None = None,
                 planner: SourceRegistrationPlanner | None = None):
        self._clients, self._definitions = dict(clients), tuple(definitions)
        self._uow_factory = uow_factory
        self._parser = parser or HistoricalTableParser()
        self._planner = planner or SourceRegistrationPlanner()

    async def _snapshots(self):
        sources = []
        for definition in self._definitions:
            source = definition.source
            package = await self._clients[source.key].get_package(source.dataset_id)
            sources.append(self._planner.select(source, package))
        self._planner.validate(sources)
        snapshots = []
        for source, definition in zip(sources, self._definitions):
            if definition.date_kind == 'published' and (
                source.resource.last_modified or '')[:10] != definition.reference_date.isoformat():
                raise SourceImportError('Historical publication date changed; review the configured snapshot.')
            table = await self._clients[source.definition.key].download_table(source.resource)
            rows = self._parser.parse(table, definition)
            snapshots.append(HistoricalSnapshot(source, rows, datetime.now(timezone.utc),
                definition.reference_date, definition.date_kind))
        return snapshots

    async def preview_import(self):
        return {'dry_run': True, 'sources': [{'source': s.source.definition.key,
            'records': len(s.rows), 'reference_date': s.reference_date.isoformat(),
            'resource_url': str(s.source.resource.url)} for s in await self._snapshots()]}

    async def import_data(self):
        if self._uow_factory is None:
            raise RuntimeError('Historical import requires a Unit of Work factory.')
        snapshots = await self._snapshots()
        results = []
        async with self._uow_factory() as work:
            for snapshot in snapshots:
                await work.sources.register(snapshot.source)
                results.append(await work.historical.import_snapshot(snapshot))
        return {'sources': results, 'records': sum(r['records'] for r in results)}
