"""LocationQuery validates filters; LocationCollection keeps map and list counts aligned."""
from datetime import date, datetime
import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from KIDSic.dto.municipality import supported_city_key
from KIDSic.dto.subsidy import SubsidyPolicy
from KIDSic.dto.historical import HistoricalEvidence

ProviderKind = Literal['municipal', 'private', 'religious', 'childminder', 'other', 'unknown']


class LocationQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')

    city: str = Field(default='Zagreb', min_length=1, max_length=100)
    q: str = Field(default='', max_length=200)
    area: str = Field(default='', max_length=200)
    age_months: int | None = Field(default=None, strict=True, ge=0, le=216)
    program: str = Field(default='', max_length=200)
    include_unknown: bool = Field(default=True, strict=True)
    provider_kind: ProviderKind | None = None
    bbox: tuple[float, float, float, float] | None = None

    @field_validator('city', 'q', 'area', 'program', mode='before')
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator('city')
    @classmethod
    def validate_city(cls, value):
        supported_city_key(value)
        return value

    @field_validator('bbox')
    @classmethod
    def validate_bbox(cls, value):
        if value is not None:
            west, south, east, north = value
            if not all(math.isfinite(x) for x in value) or not (
                -180 <= west <= east <= 180 and -90 <= south <= north <= 90
            ):
                raise ValueError('bbox must be west,south,east,north within WGS84 bounds.')
        return value


class LocationSource(BaseModel):
    name: str
    url: str
    license: str | None = None
    reference_date: date | None
    retrieved_at: datetime


class LocationFieldSource(LocationSource):
    active_snapshot: bool


class LocationProgram(BaseModel):
    program_id: str
    name: str
    min_age_months: int | None
    max_age_months_exclusive: int | None
    verified_on: date
    valid_until: date | None
    source_record_id: str
    source_url: str
    source_title: str
    scope: Literal['institution', 'facility']


class LocationProperties(BaseModel):
    location_id: str | None
    kindergarten_id: str
    name: str
    location_name: str
    address: str | None
    city: str
    provider_kind: ProviderKind
    website_url: str | None = None
    email: str | None = None
    phone: str | None = None
    district: str | None
    areas: list[str] = Field(default_factory=list)
    location_role: Literal['facility', 'seat']
    sources: list[LocationSource]
    field_sources: dict[str, LocationFieldSource] = Field(default_factory=dict)
    subsidy_policies: list[SubsidyPolicy] = Field(default_factory=list)
    suitability_status: Literal['not_evaluated', 'confirmed', 'unknown'] = 'not_evaluated'
    programs: list[LocationProgram] = Field(default_factory=list)
    historical_data: list[HistoricalEvidence] = Field(default_factory=list)
    # Retained for older clients; the sourced programs carry explicit age bounds.
    age_groups: None = None


class LocationPoint(BaseModel):
    type: Literal['Point'] = 'Point'
    coordinates: tuple[float, float]


class LocationFeature(BaseModel):
    type: Literal['Feature'] = 'Feature'
    id: str
    geometry: LocationPoint | None
    properties: LocationProperties


class LocationMetadata(BaseModel):
    total: int
    mapped: int
    unmapped: int
    scope: Literal['city', 'bbox']
    complete: Literal[True] = True
    confirmed: int = Field(default=0, ge=0)
    unknown: int = Field(default=0, ge=0)


class LocationCollection(BaseModel):
    type: Literal['FeatureCollection'] = 'FeatureCollection'
    features: list[LocationFeature]
    metadata: LocationMetadata
