from KIDSic.config.historical import zagreb_historical_sources
from KIDSic.integrations.concrete.ckan import CkanClient
from KIDSic.services.concrete.historical import HistoricalService


class HistoricalServiceFactory:
    def __init__(self, settings):
        self._settings = settings

    def create(self, http, uow_factory=None, source_keys=None):
        settings = self._settings
        definitions = zagreb_historical_sources(settings.ckan_zagreb_base_url)
        if source_keys is not None:
            if set(source_keys) - {d.source.key for d in definitions}:
                raise ValueError('Unknown historical source.')
            definitions = tuple(d for d in definitions if d.source.key in source_keys)
        clients = {d.source.key: CkanClient(http, d.source.base_url, settings.ckan_timeout,
            settings.ckan_max_bytes, csv_encoding=d.source.csv_encoding) for d in definitions}
        return HistoricalService(clients, definitions, uow_factory)
