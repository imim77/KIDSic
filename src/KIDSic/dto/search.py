"""Framework-independent data exchanged by the search service."""
from typing import NotRequired, TypedDict


class SearchCriteria(TypedDict):
    city: str
    age_months: int
    area: NotRequired[str]


class Recommendation(TypedDict):
    criteria: SearchCriteria
    confirmed: list[dict]
    age_unknown: list[dict]
    context: list[dict]
    notice: str
