"""LocationQuery validates filters; LocationCollection keeps map and list counts aligned."""
from datetime import date, datetime
import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from KIDSic.dto.municipality import supported_city_key
from KIDSic.dto.subsidy import SubsidyPolicy
from KIDSic.dto.historical import HistoricalEvidence

ProviderKind = Literal['municipal', 'private', 'religious', 'childminder', 'other', 'unknown']


class LocationQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')

    city: str = Field(default='Zagreb', min_length=1, max_length=100)
    q: str = Field(default='', max_length=200)
    area: str = Field(default='', max_length=200)
    # has_vacancies keeps objects whose latest published vacancy snapshot lists
    # at least one free place; unpublished counts never match.
    has_vacancies: bool = Field(default=False, strict=True)
    provider_kind: ProviderKind | None = None
    bbox: tuple[float, float, float, float] | None = None
    # near and radius_m select points within a straight-line radius; objects
    # without verified coordinates cannot be asserted inside it.
    near: tuple[float, float] | None = None
    radius_m: int | None = Field(default=None, strict=True, ge=1, le=50_000)

    @field_validator('city', 'q', 'area', mode='before')
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

    @field_validator('near')
    @classmethod
    def validate_near(cls, value):
        if value is not None:
            longitude, latitude = value
            if not all(math.isfinite(x) for x in value) or not (
                -180 <= longitude <= 180 and -90 <= latitude <= 90
            ):
                raise ValueError('near must be longitude,latitude within WGS84 bounds.')
        return value

    # One spatial scope keeps metadata.scope unambiguous.
    @model_validator(mode='after')
    def validate_radius(self):
        if (self.near is None) != (self.radius_m is None):
            raise ValueError('near and radius_m must be given together.')
        if self.near is not None and self.bbox is not None:
            raise ValueError('Use either bbox or near with radius_m.')
        return self


class LocationSource(BaseModel):
    name: str
    url: str
    license: str | None = None
    reference_date: date | None
    retrieved_at: datetime


class LocationFieldSource(LocationSource):
    active_snapshot: bool


class LocationEnrolment(BaseModel):
    # LocationEnrolment is one published round with its official channel. The
    # status compares the round's own times with one clock reading; it never
    # promises a place. Steps and documents are read from the cited source.
    round: Literal['main', 'rolling']
    academic_year: str
    channel: Literal['e_upisi', 'city_system', 'kindergarten']
    application_url: str
    accepting: bool
    opens_at: datetime | None
    closes_at: datetime | None
    status: Literal['open', 'upcoming', 'closed', 'not_accepting', 'dates_unknown']
    source_title: str
    source_url: str
    license: str | None = None
    reference_date: date | None
    date_kind: Literal['published', 'observed', 'unknown']


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
    historical_data: list[HistoricalEvidence] = Field(default_factory=list)
    enrolment: list[LocationEnrolment] = Field(default_factory=list)
    distance_m: int | None = None  # Straight-line metres from near; null without it.


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
    scope: Literal['city', 'bbox', 'radius']
    complete: Literal[True] = True


class LocationCollection(BaseModel):
    type: Literal['FeatureCollection'] = 'FeatureCollection'
    features: list[LocationFeature]
    metadata: LocationMetadata
