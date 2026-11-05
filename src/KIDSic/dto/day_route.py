"""DayJourneyRequest bounds Rijeka commute inputs and interprets wall times in Zagreb."""
from datetime import date, datetime, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator

ZAGREB = ZoneInfo('Europe/Zagreb')
GTFS_SHA256 = 'e2d9357c5f020d6d4081ba114509d89f51a33dd224d09aae09ff6c1e4c0849bd'
GTFS_URL = ('https://gitlab.com/api/v4/projects/vekejsn%2Fgtfs-generators/'
            'packages/generic/rijeka-gtfs/latest/autotrolej_gtfs.zip')
SERVICE_START = date(2026, 10, 9)
SERVICE_END = date(2026, 11, 8)


class DayPoint(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    lat: float = Field(ge=45.20, le=45.45)
    lon: float = Field(ge=14.20, le=14.65)


class DayJourneyRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
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
        if not SERVICE_START <= value.date() <= SERVICE_END:
            raise ValueError('Date is outside the pinned timetable range.')
        return value

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
