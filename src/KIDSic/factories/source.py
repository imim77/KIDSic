from KIDSic.dto.source import SourceDefinition
from KIDSic.integrations.concrete.ckan import CkanClient
from KIDSic.services.concrete.source import SourceService
from KIDSic.services.interfaces.source import SourceServiceInterface


class SourceServiceFactory:
    def __init__(self, settings):
        self._settings = settings

    def create(self, http, uow_factory=None, source_keys=None) -> SourceServiceInterface:
        settings = self._settings
        definitions = (
            SourceDefinition('national', settings.ckan_base_url, settings.ckan_dataset_id, 'national'),
            SourceDefinition('zagreb-municipal', settings.ckan_zagreb_base_url,
                             settings.ckan_zagreb_municipal_dataset_id, 'municipal'),
            SourceDefinition('zagreb-other', settings.ckan_zagreb_base_url,
                             settings.ckan_zagreb_other_dataset_id, 'other'),
            SourceDefinition('varazdin-childminders', settings.ckan_base_url,
                             settings.ckan_varazdin_childminders_dataset_id, 'varazdin-childminders',
                             resource_format='csv', resource_id=settings.ckan_varazdin_childminders_resource_id),
        )
        if source_keys is not None:
            unknown = set(source_keys) - {d.key for d in definitions}
            if unknown:
                raise ValueError(f'Unknown source keys: {sorted(unknown)}')
            definitions = tuple(d for d in definitions if d.key in source_keys)
        clients = {d.key: CkanClient(http, d.base_url, settings.ckan_timeout,
                                    settings.ckan_max_bytes) for d in definitions}
        return SourceService(clients, definitions, uow_factory)
