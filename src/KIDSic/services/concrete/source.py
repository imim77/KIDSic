"""Plan before writing, following FOIHireloom's source-registration workflow."""
from datetime import datetime, timezone
from collections.abc import Mapping, Sequence
from KIDSic.db.uow.source import SourceUnitOfWorkFactory
from KIDSic.integrations.interfaces.ckan import CkanClientInterface

from KIDSic.dto.source import SourceSnapshot, SourceDefinition
from KIDSic.services.concrete.parsers import default_parsers
from KIDSic.services.concrete.source_normalizer import SourceRecordNormalizer
from KIDSic.services.concrete.source_planner import SourceRegistrationPlanner
from KIDSic.services.interfaces.source import SourceServiceInterface


class SourceService(SourceServiceInterface):
    def __init__(self, clients: Mapping[str, CkanClientInterface],
                 definitions: Sequence[SourceDefinition],
                 uow_factory: SourceUnitOfWorkFactory | None = None, *,
                 normalizer: SourceRecordNormalizer | None = None,
                 planner: SourceRegistrationPlanner | None = None):
        self._normalizer = normalizer or SourceRecordNormalizer(default_parsers())
        self._planner = planner or SourceRegistrationPlanner()
        self._clients = dict(clients)
        self._definitions = tuple(definitions)
        self._uow_factory = uow_factory

    async def _plan(self):
        sources = []
        for definition in self._definitions:
            package = await self._clients[definition.key].get_package(definition.dataset_id)
            sources.append(self._planner.select(definition, package))
        self._planner.validate(sources)
        return sources

    @staticmethod
    def _summary(sources):
        return [{'source': s.definition.key, 'title': s.package.title,
                 'publisher': s.publisher, 'catalogue_url': s.catalogue_url,
                 'license': s.package.license_title or s.package.license_id,
                 **s.metadata} for s in sources]

    def _require_database(self):
        if self._uow_factory is None:
            raise RuntimeError('This operation requires a Unit of Work factory.')

    async def preview_sources(self):
        return {'dry_run': True, 'sources': self._summary(await self._plan())}

    async def register_sources(self):
        self._require_database()
        sources = await self._plan()
        counts = dict(added=0, updated=0, unchanged=0)
        async with self._uow_factory() as work:
            for source in sources:
                counts[await work.sources.register(source)] += 1
        return {'sources': len(sources), **counts}

    async def _snapshots(self):
        snapshots = []
        for source in await self._plan():
            records = await self._clients[source.definition.key].download_records(source.resource)
            rows = self._normalizer.normalize(records, source.definition.parser)
            snapshots.append(SourceSnapshot(source, rows, datetime.now(timezone.utc)))
        return snapshots

    async def preview_import(self):
        snapshots = await self._snapshots()
        return {'dry_run': True, 'sources': [
            {'source': s.source.definition.key, 'records': len(s.rows),
             'settlements': len({r.settlement for r in s.rows}),
             'resource_url': str(s.source.resource.url)} for s in snapshots]}

    async def import_data(self, *, allow_removals: bool = False):
        self._require_database()
        snapshots = await self._snapshots()
        async with self._uow_factory() as work:
            results = [await work.sources.import_snapshot(snapshot, allow_removals=allow_removals)
                       for snapshot in snapshots]
        return {'sources': results, 'records': sum(r['records'] for r in results)}
