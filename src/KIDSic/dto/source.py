"""Validated metadata plans and normalized rows passed to persistence."""
from dataclasses import dataclass
from datetime import datetime
import re

from KIDSic.dto.ckan import CkanPackage, CkanResource
from KIDSic.dto.text import normalize


def name_key(value: str) -> str:
    value = re.sub(r'\bdjecji\s+vrtic\b', 'dv', normalize(value))
    return re.sub(r'[^\w]+', ' ', value).strip()


@dataclass(frozen=True)
class SourceDefinition:
    key: str
    base_url: str
    dataset_id: str
    parser: str
    resource_format: str = 'json'
    resource_id: str | None = None
    license_id: str = 'open-license'
    csv_encoding: str = 'utf-8-sig'


@dataclass(frozen=True)
class PlannedSource:
    definition: SourceDefinition
    package: CkanPackage
    resource: CkanResource

    @property
    def catalogue_url(self) -> str:
        return f'{self.definition.base_url.rstrip("/")}/dataset/{self.package.name}'

    @property
    def publisher(self) -> str:
        return (self.package.organization or {}).get('title') or 'Unknown publisher'

    @property
    def metadata(self) -> dict:
        return {
            'ckan_base_url': self.definition.base_url.rstrip('/'),
            'ckan_package_id': self.package.id,
            'ckan_resource_id': self.resource.id,
            'resource_url': str(self.resource.url),
            'resource_format': self.resource.format,
            'resource_modified_at': self.resource.last_modified,
            'catalogue_modified_at': self.package.metadata_modified,
            'license_id': self.package.license_id,
            'license_url': self.package.license_url,
        }


@dataclass(frozen=True)
class KindergartenRow:
    source_key: str
    raw_data: dict
    name: str
    location_name: str
    settlement: str
    address: str

    scope: str = 'location'
    municipality: str | None = None
    oib: str | None = None
    provider_kind: str = 'unknown'
    provider_kind_source_url: str | None = None
    kind: str = 'unknown'
    postal_code: str | None = None
    county: str | None = None
    district: str | None = None
    email: str | None = None
    phone: str | None = None
    website_url: str | None = None
    longitude: float | None = None
    latitude: float | None = None


@dataclass(frozen=True)
class SourceSnapshot:
    source: PlannedSource
    rows: tuple[KindergartenRow, ...]
    fetched_at: datetime
