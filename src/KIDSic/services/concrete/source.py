"""Plan before writing, following FOIHireloom's source-registration workflow."""
from datetime import datetime, timezone

from KIDSic.dto.source import PlannedSource, SourceSnapshot
from KIDSic.exceptions import SourceImportError
from KIDSic.services.concrete.kindergarten_normalizer import normalize_records
from KIDSic.services.interfaces.source import SourceServiceInterface


class SourceService(SourceServiceInterface):
    def __init__(self, clients, definitions, uow_factory=None):
        self._clients = clients
        self._definitions = definitions
        self._uow_factory = uow_factory

    async def _plan(self):
        sources = []
        identities, urls = set(), set()
        for definition in self._definitions:
            package = await self._clients[definition.key].get_package(definition.dataset_id)
            # A changed/absent licence requires review, not implicit approval.
            if package.license_id != 'open-license':
                raise SourceImportError(f'{definition.key}: expected Otvorena dozvola (open-license).')
            formats = {'json': {'json', 'application/json'}, 'csv': {'csv', 'text/csv'}}
            expected = formats[definition.resource_format]
            resources = [r for r in package.resources if r.state == 'active'
                         and (r.format or '').strip().casefold() in expected
                         and (definition.resource_id is None or r.id == definition.resource_id)]
            if len(resources) != 1:
                raise SourceImportError(f'{definition.key}: expected exactly one active {definition.resource_format.upper()} resource matching the configured identity.')
            resource = resources[0]
            identity = (definition.base_url.rstrip('/'), resource.id)
            if identity in identities or str(resource.url) in urls:
                raise SourceImportError('Multiple datasets identify the same resource.')
            identities.add(identity)
            urls.add(str(resource.url))
            sources.append(PlannedSource(definition, package, resource))
        if not sources:
            raise SourceImportError('Select at least one source.')
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
            rows = normalize_records(records, source.definition.parser)
            snapshots.append(SourceSnapshot(source, rows, datetime.now(timezone.utc)))
        return snapshots

    async def preview_import(self):
        snapshots = await self._snapshots()
        return {'dry_run': True, 'sources': [
            {'source': s.source.definition.key, 'records': len(s.rows),
             'settlements': len({r.settlement for r in s.rows}),
             'resource_url': str(s.source.resource.url)} for s in snapshots]}

    async def import_data(self):
        self._require_database()
        snapshots = await self._snapshots()
        async with self._uow_factory() as work:
            results = [await work.sources.import_snapshot(snapshot) for snapshot in snapshots]
        return {'sources': results, 'records': sum(r['records'] for r in results)}
