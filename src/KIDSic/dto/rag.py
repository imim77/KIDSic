"""RagContext carries attributed excerpts for the host model's answer."""
from datetime import date
from typing import Literal, get_args
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from KIDSic.dto.municipality import supported_city_key

Topic = Literal['programs', 'vacancies', 'subsidies', 'contacts', 'document']
TOPICS: tuple[Topic, ...] = get_args(Topic)


class RagQuery(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    city: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    topics: list[Topic] | None = Field(default=None, min_length=1)
    feature_id: str | None = Field(default=None, max_length=50)

    @field_validator('city')
    @classmethod
    def validate_city(cls, value):
        supported_city_key(value)
        return value

    @field_validator('topics')
    @classmethod
    def deduplicate_topics(cls, value):
        return None if value is None else list(dict.fromkeys(value))

    @field_validator('feature_id')
    @classmethod
    def validate_feature(cls, value):
        if value is not None:
            UUID(value.removeprefix('seat:'))
        return value


class RagMatch(BaseModel):
    feature_id: str
    kindergarten_id: str
    name: str
    location_name: str
    address: str | None
    city: str


class RagSource(BaseModel):
    title: str
    url: str
    license: str | None = None


class RagEvidence(BaseModel):
    citation_id: str
    kindergarten_id: str
    location_id: str | None
    applies_to: list[str]
    scope: Literal['facility', 'institution', 'municipality']
    topic: Topic
    temporal_status: Literal['historical', 'current', 'undated']
    reference_date: date | None
    date_kind: Literal['published', 'observed', 'verified', 'unknown']
    content: str
    sources: list[RagSource]


class RagContext(BaseModel):
    criteria: RagQuery
    status: Literal['ok', 'not_found', 'clarification_required', 'no_evidence']
    total_matches: int
    matches: list[RagMatch] = Field(default_factory=list)
    evidence: list[RagEvidence] = Field(default_factory=list)
    truncated: bool = False
    notice: str
