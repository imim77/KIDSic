"""Pinned resources distinguish source snapshots from catalogue modification dates."""
from datetime import date
from KIDSic.dto.historical import HistoricalSourceDefinition
from KIDSic.dto.source import SourceDefinition


def zagreb_historical_sources(base_url: str):
    vacancies = 'slobodna-mjesta-u-vrticima-i-obrtima-za-cuvanje-djece-grada-zagreba'
    return (
        HistoricalSourceDefinition(SourceDefinition('zagreb-programs-2019',base_url,
            'djecji-vrtici-grada-zagreba','programs',resource_format='xlsx',
            resource_id='b94a968b-be3a-410b-84d3-2e5a857b311d'),date(2019,10,9),'published'),
        HistoricalSourceDefinition(SourceDefinition('zagreb-vacancies-2025',base_url,
            vacancies,'municipal-vacancies',resource_format='csv',
            resource_id='a6a9199d-eaf4-4f75-9bce-7a3a5b367d30'),date(2025,1,1),'observed'),
        HistoricalSourceDefinition(SourceDefinition('zagreb-childminder-vacancies-2025',base_url,
            vacancies,'childminder-vacancies',resource_format='csv',
            resource_id='f1c42d5e-17c8-40e9-83a9-fba7539bd4b5'),date(2025,1,1),'observed'),
    )
