# Location read API

`GET /api/locations` returns a complete GeoJSON FeatureCollection of accepted
records in import-approved sources' active snapshots. It does not alter the
existing conversational search. No authentication is required for this public
read endpoint; the local server binds to `127.0.0.1` by default.

| Query | Meaning |
| --- | --- |
| `city` | Settlement or municipality name/curated alias, default `Zagreb`. Trimmed, 1–100 characters. A municipality includes its settlements. |
| `q` | Literal case-insensitive substring of institution or facility name, trimmed, at most 200 characters. No address search. |
| `provider_kind` | One of `municipal`, `private`, `religious`, `childminder`, `other`, `unknown`; omitted means all. |
| `bbox` | Optional `west,south,east,north` in WGS84; finite ordered longitude/latitude bounds. Antimeridian wrapping is unsupported. |

There is no pagination or result cap: `metadata.complete` is always `true` and
`total` equals the feature count. `mapped + unmapped = total`. Without `bbox`,
`scope` is `city` and features without coordinates remain available for the list.
With `bbox`, `scope` is `bbox` and only points within the inclusive bounds are
returned; unknown coordinates cannot be asserted inside the box. Analysis callers
must omit `bbox` to obtain the complete selected city, independently of map view.
Unsupported query parameters, repeated parameters and invalid filters return
HTTP 422 with `{"error":"invalid_query"}`. Database unavailable returns HTTP 503
with `{"error":"locations_unavailable"}`; internal exception text is never sent.

Each active facility appears once by canonical location ID even when multiple
sources attest it. An institution seat appears only when the institution has no
active facility, even if that facility is outside the requested city or box.
Seat IDs use `seat:<kindergarten_id>`, `location_id` is null, and geometry is null:
a legal seat is not treated as a confirmed service location. An unlocated active
facility also has null geometry but retains its facility ID and role. Sources
include the active records' reference date (null when unknown), fetch timestamp,
source URL/title and license (null when unrecorded). No missing coordinates,
reference dates, licenses or age groups are inferred. Age evidence remains
available through the existing age-aware search; `age_groups: null` here means
unknown and is not an enrolment or capacity claim.

Illustrative response (identities and values below are synthetic):

```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "id": "00000000-0000-0000-0000-000000000001",
    "geometry": {"type": "Point", "coordinates": [15.98, 45.81]},
    "properties": {
      "location_id": "00000000-0000-0000-0000-000000000001",
      "kindergarten_id": "00000000-0000-0000-0000-000000000002",
      "name": "Primjer ustanove", "location_name": "Primjer objekta",
      "address": "Primjer 1", "city": "Zagreb", "provider_kind": "municipal",
      "district": null, "location_role": "facility", "age_groups": null,
      "sources": [{"name": "Primjer izvora", "url": "https://example.invalid",
        "license": null, "reference_date": null,
        "retrieved_at": "2026-11-02T10:00:00Z"}]
    }
  }],
  "metadata": {"total": 1, "mapped": 1, "unmapped": 0,
    "scope": "city", "complete": true}
}
```

The Python contract lives in `src/KIDSic/dto/location.py` and is independent of
HTTP. All database reads for a request share the existing repeatable-read,
read-only Unit of Work. Source activation remains the import pipeline's job.
