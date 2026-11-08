"""Enrolment fixtures keep example documents separate from production snapshots."""

DOCUMENT = {
    "dataset_key": "example-enrolment",
    "title": "Obavijest o upisu",
    "publisher": "Grad Zagreb",
    "url": "https://example.invalid/upis.pdf",
    "license": "Ponovna uporaba uz navođenje izvora",
    "license_url": "https://example.invalid/uvjeti",
    "municipality": "zagreb",
    "provider_kinds": ["municipal"],
    "reference_date": "2026-05-11",
    "date_kind": "published",
    "valid_until": "2027-08-31",
    "excerpts": [
        {"content": "Zahtjevi se podnose od 13. svibnja 2026. do 22. svibnja 2026."}
    ],
}


CALL = {
    "round": "main",
    "academic_year": "2026./2027.",
    "channel": "city_system",
    "application_url": "https://upis.example.invalid",
    "opens_at": "2026-05-13T09:00:00+02:00",
    "closes_at": "2026-05-22T16:00:00+02:00",
}


ROUND = {
    "round": "main",
    "academic_year": "2026./2027.",
    "channel": "city_system",
    "application_url": "https://upis.example.invalid",
    "accepting": True,
    "opens_at": "2026-05-13T07:00:00+00:00",
    "closes_at": "2026-05-22T14:00:00+00:00",
    "source_title": "Obavijest",
    "source_url": "https://example.invalid/upis.pdf",
    "license": None,
    "reference_date": "2026-05-11",
    "date_kind": "published",
}
