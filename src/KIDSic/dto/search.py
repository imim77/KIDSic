"""Framework-independent data exchanged by the search service."""
from typing import TypedDict


class SearchCriteria(TypedDict):
    city: str
    age_months: int


class Recommendation(TypedDict):
    criteria: SearchCriteria
    confirmed: list[dict]
    age_unknown: list[dict]
    context: list[dict]
    notice: str
