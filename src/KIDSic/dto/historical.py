"""Historical snapshots retain source dates without asserting current eligibility."""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field
from KIDSic.dto.source import SourceDefinition, PlannedSource


class HistoricalVacancy(BaseModel):
    age_label: str | None = None
    program: str | None = None
    free_places: int | None = Field(ge=0)


class HistoricalEvidence(BaseModel):
    reference_date: date
    date_kind: Literal['published', 'observed']
    scope: Literal['facility', 'institution']
    programs: list[str] = Field(default_factory=list)
    vacancies: list[HistoricalVacancy] = Field(default_factory=list)
    source_title: str
    source_url: str
    license: str


@dataclass(frozen=True)
class HistoricalSourceDefinition:
    source: SourceDefinition
    reference_date: date
    date_kind: Literal['published', 'observed']


@dataclass(frozen=True)
class HistoricalRow:
    source_key: str
    name: str
    address: str | None
    provider_kind: str
    scope: str
    raw_data: dict
    programs: tuple[str, ...] = ()
    vacancies: tuple[HistoricalVacancy, ...] = ()


@dataclass(frozen=True)
class HistoricalSnapshot:
    source: PlannedSource
    rows: tuple[HistoricalRow, ...]
    fetched_at: datetime
    reference_date: date
    date_kind: str
