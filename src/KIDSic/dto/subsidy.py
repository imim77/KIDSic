"""SubsidyPolicy exposes descriptive funding evidence without deciding eligibility."""
from datetime import date
from pydantic import BaseModel, Field
from typing import Literal


class SubsidyRate(BaseModel):
    label: str
    city_subsidy_cents: int | None = None
    parent_fee_cents: int | None = None


class SubsidySource(BaseModel):
    title: str
    url: str


class SubsidyPolicy(BaseModel):
    policy_key: str
    title: str
    summary: str
    verification_status: Literal['verified', 'partial']
    verified_on: date
    valid_from: date | None
    valid_until: date | None
    amount_kind: Literal['city_subsidy', 'parent_fee']
    rates: list[SubsidyRate] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    reliefs: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    sources: list[SubsidySource]
