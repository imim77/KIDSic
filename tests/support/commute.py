"""Commute fixtures provide synthetic Rijeka criteria and facilities."""

from KIDSic.dto.location import LocationFeature


def criteria(**changes):
    return {
        "city": "Rijeka",
        "home": {"lat": 45.338, "lon": 14.410},
        "work": {"lat": 45.3271, "lon": 14.4422},
        "departure": "2026-11-05T07:00",
        "mode": "TRANSIT",
    } | changes


def facility(identifier, longitude=14.42, name=None):
    return LocationFeature(
        id=identifier,
        geometry={"coordinates": (longitude, 45.33)},
        properties={
            "location_id": identifier,
            "kindergarten_id": "synthetic",
            "name": name or identifier,
            "location_name": name or identifier,
            "address": "Test 1",
            "city": "Rijeka",
            "provider_kind": "municipal",
            "district": None,
            "location_role": "facility",
            "sources": [],
        },
    )
