"""LocationQuery validates filters; LocationCollection keeps map and list counts aligned."""
from datetime import date, datetime
import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ProviderKind = Literal['municipal', 'private', 'religious', 'childminder', 'other', 'unknown']


class LocationQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')

    city: str = Field(default='Zagreb', min_length=1, max_length=100)
    q: str = Field(default='', max_length=200)
    provider_kind: ProviderKind | None = None
    bbox: tuple[float, float, float, float] | None = None

    @field_validator('city', 'q', mode='before')
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

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


class LocationProperties(BaseModel):
    location_id: str | None
    kindergarten_id: str
    name: str
    location_name: str
    address: str | None
    city: str
    provider_kind: ProviderKind
    district: str | None
    location_role: Literal['facility', 'seat']
    sources: list[LocationSource]
    field_sources: dict[str, LocationFieldSource] = Field(default_factory=dict)
    # Age suitability is not evaluated by this endpoint.
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


class LocationCollection(BaseModel):
    type: Literal['FeatureCollection'] = 'FeatureCollection'
    features: list[LocationFeature]
    metadata: LocationMetadata
