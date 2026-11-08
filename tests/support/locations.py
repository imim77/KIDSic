"""Location fixtures construct valid empty map responses."""

from KIDSic.dto.location import LocationCollection


def empty_collection():
    return LocationCollection(
        features=[],
        metadata={
            "total": 0,
            "mapped": 0,
            "unmapped": 0,
            "scope": "city",
        },
    )
