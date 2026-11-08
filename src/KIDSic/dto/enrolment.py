"""Reviewed enrolment documents keep source, scope and dates with every excerpt."""
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class EnrolmentExcerpt(BaseModel):


    model_config = ConfigDict(extra='forbid', frozen=True)
    content: str = Field(min_length=1, max_length=4000)
    institutions: tuple[str, ...] = ()


class EnrolmentCall(BaseModel):




    model_config = ConfigDict(extra='forbid', frozen=True)
    round: Literal['main', 'rolling']
    academic_year: str = Field(pattern=r'^\d{4}\./\d{4}\.$')
    channel: Literal['e_upisi', 'city_system', 'kindergarten']
    application_url: HttpUrl
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    not_accepting: tuple[str, ...] = ()

    @model_validator(mode='after')
    def check_period(self):
        for value in (self.opens_at, self.closes_at):
            if value is not None and value.tzinfo is None:
                raise ValueError('Enrolment times need an explicit UTC offset.')
        if self.opens_at and self.closes_at and self.closes_at < self.opens_at:
            raise ValueError('closes_at must not precede opens_at.')
        return self


class EnrolmentDocument(BaseModel):



    model_config = ConfigDict(extra='forbid', frozen=True)
    dataset_key: str = Field(pattern=r'^[a-z0-9-]+$')
    title: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    url: HttpUrl
    license: str = Field(min_length=1)
    license_url: HttpUrl
    municipality: Literal['zagreb', 'varazdin', 'rijeka', 'sibenik']
    provider_kinds: tuple[Literal['municipal', 'private', 'religious', 'childminder', 'other'], ...] = Field(min_length=1)
    institutions: tuple[str, ...] = ()
    reference_date: date
    date_kind: Literal['published', 'observed']
    valid_until: date | None = None
    sha256: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')
    excerpts: tuple[EnrolmentExcerpt, ...] = Field(min_length=1)
    calls: tuple[EnrolmentCall, ...] = ()

    @model_validator(mode='after')
    def check_scope(self):
        if self.valid_until is not None and self.valid_until < self.reference_date:
            raise ValueError('valid_until must not precede reference_date.')
        named = {name for e in self.excerpts for name in e.institutions}
        outside = (named | {name for c in self.calls for name in c.not_accepting}) - set(self.institutions)
        if self.institutions and outside:
            raise ValueError(f'Excerpt institutions outside the document scope: {sorted(outside)}')
        return self


class EnrolmentSnapshot(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    snapshot_key: str = Field(min_length=1)
    verified_on: date
    documents: tuple[EnrolmentDocument, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def check_unique_sources(self):
        keys = [d.dataset_key for d in self.documents]
        if len(keys) != len(set(keys)):
            raise ValueError('Each document needs its own dataset_key.')
        return self
