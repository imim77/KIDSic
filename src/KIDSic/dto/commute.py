"""CommuteQuery carries explicit chat criteria without guessing coordinates."""
from typing import Literal

from pydantic import Field, field_validator

from KIDSic.dto.day_route import DayJourneyRequest, DayPoint


class CommuteQuery(DayJourneyRequest):
    city: Literal['Rijeka', 'Zagreb', 'Šibenik']
    home: DayPoint | str
    work: DayPoint | str
    mode: Literal['WALK', 'TRANSIT']


    kindergartens: list[str] | None = Field(default=None, min_length=1, max_length=20)

    @field_validator('home', 'work')
    @classmethod
    def address_or_point(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not 3 <= len(value) <= 200:
                raise ValueError('Supply a street address or explicit coordinates.')
        return value

    @field_validator('kindergartens')
    @classmethod
    def kindergarten_names(cls, value):
        if value is None:
            return value
        names = list(dict.fromkeys(name.strip() for name in value))
        if any(not 2 <= len(name) <= 120 for name in names):
            raise ValueError('Name each kindergarten with 2 to 120 characters.')
        return names
