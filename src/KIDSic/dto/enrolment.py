"""Reviewed enrolment documents keep source, scope and dates with every excerpt."""
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class EnrolmentExcerpt(BaseModel):
    # EnrolmentExcerpt is one self-contained passage; conditions and dates are
    # never split across excerpts. Named institutions narrow its scope.
    model_config = ConfigDict(extra='forbid', frozen=True)
    content: str = Field(min_length=1, max_length=4000)
    institutions: tuple[str, ...] = ()


class EnrolmentDocument(BaseModel):
    # EnrolmentDocument describes one official source with a confirmed reuse
    # licence. Without `institutions` it covers every active provider of the
    # given kinds in the municipality; with them, only those institutions.
    model_config = ConfigDict(extra='forbid', frozen=True)
    dataset_key: str = Field(pattern=r'^[a-z0-9-]+$')
    title: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    url: HttpUrl
    license: str = Field(min_length=1)
    license_url: HttpUrl
    municipality: Literal['zagreb', 'varazdin', 'rijeka']
    provider_kinds: tuple[Literal['municipal', 'private', 'religious', 'childminder', 'other'], ...] = Field(min_length=1)
    institutions: tuple[str, ...] = ()
    reference_date: date
    date_kind: Literal['published', 'observed']
    valid_until: date | None = None  # Inclusive end of the period the document governs.
    sha256: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')
    excerpts: tuple[EnrolmentExcerpt, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def check_scope(self):
        if self.valid_until is not None and self.valid_until < self.reference_date:
            raise ValueError('valid_until must not precede reference_date.')
        outside = {name for e in self.excerpts for name in e.institutions} - set(self.institutions)
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
