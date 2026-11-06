"""DayJourneyRequest bounds city commute inputs and interprets wall times in Zagreb."""
from datetime import datetime, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from KIDSic.config.routing import ROUTING_CITIES

ZAGREB = ZoneInfo('Europe/Zagreb')


class DayPoint(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    lat: float = Field(ge=43.60, le=46.00)
    lon: float = Field(ge=14.20, le=16.30)


class DayJourneyRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    city: Literal['Rijeka', 'Zagreb', 'Šibenik'] = 'Rijeka'
    home: DayPoint
    work: DayPoint
    departure: datetime
    mode: Literal['WALK', 'TRANSIT'] = 'TRANSIT'
    top_k: int = Field(default=4, strict=True, ge=1)
    dropoff_minutes: int = Field(default=10, strict=True, ge=0, le=60)

    @field_validator('departure')
    @classmethod
    def local_time(cls, value):
        if value.tzinfo is None:
            local = value.replace(tzinfo=ZAGREB)
            if (local.astimezone(timezone.utc).astimezone(ZAGREB).replace(tzinfo=None) != value
                    or local.utcoffset() != local.replace(fold=1).utcoffset()):
                raise ValueError('Use an explicit offset at a daylight-saving transition.')
            value = local
        value = value.astimezone(ZAGREB)
        return value

    @model_validator(mode='after')
    def city_coverage(self):
        city = ROUTING_CITIES[self.city]
        for point in (self.home, self.work):
            # CommuteQuery also accepts unresolved address strings.
            if isinstance(point, DayPoint) and not city.contains(point.lat, point.lon):
                raise ValueError(f'Coordinates are outside {city.name} routing coverage.')
        if not city.service_start <= self.departure.date() <= city.service_end:
            raise ValueError(f'{city.name} timetable covers {city.service_start}–{city.service_end}.')
        return self


class RouteLeg(BaseModel):
    mode: str
    departure: datetime
    arrival: datetime
    from_name: str
    to_name: str
    line: str | None = None
    geometry: str | None = None


class Journey(BaseModel):
    departure: datetime
    arrival: datetime
    legs: list[RouteLeg]
