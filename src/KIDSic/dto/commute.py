"""CommuteQuery carries explicit chat criteria without guessing coordinates."""
from typing import Literal

from pydantic import field_validator

from KIDSic.dto.day_route import DayJourneyRequest, DayPoint


class CommuteQuery(DayJourneyRequest):
    city: Literal['Rijeka']
    home: DayPoint | str
    work: DayPoint | str
    mode: Literal['WALK', 'TRANSIT']  # Ask instead of silently choosing transport.

    @field_validator('home', 'work')
    @classmethod
    def address_or_point(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not 3 <= len(value) <= 200:
                raise ValueError('Supply a street address or explicit coordinates.')
        return value
