# Location read API

`GET /api/locations` returns a complete GeoJSON FeatureCollection of accepted
records in import-approved sources' active snapshots. No authentication is required for this public
read endpoint; the local server binds to `127.0.0.1` by default.

| Query | Meaning |
| --- | --- |
| `city` | `Zagreb`, `Varaždin`, `Rijeka` or `Šibenik`, including case/diacritic variants and curated aliases, default `Zagreb`. Trimmed, 1–100 characters. Each city includes its settlements, such as Sesvete within Zagreb. Other cities return HTTP 422. |
| `q` | Literal substring of institution or facility name, ignoring case and Croatian diacritics (č/ć/ž/š/đ), trimmed, at most 200 characters. `%` and `_` are literal characters. No address search. |
| `provider_kind` | One of `municipal`, `private`, `religious`, `childminder`, `other`, `unknown`; omitted means all. |
| `area` | Jedan točan naziv četvrti, predjela ili naselja, triman, do 200 znakova; izostavljeno ili prazno znači sva područja. Podudaranje zanemaruje velika slova i hrvatske dijakritike te opcionalni prefiks `Mjesni odbor `. Kombinira se s ostalim filtrima logikom AND. |
| `has_vacancies` | `true` keeps objects whose newest published vacancy snapshot in `historical_data` lists at least one free place; `false` (default) applies no filter. A newer published zero replaces an older positive count, and unpublished or blank counts never match. Snapshots are dated, often per institution, and are not a guarantee of a place. HTTP requires literal `true` or `false`. |
| `bbox` | Optional `west,south,east,north` in WGS84; finite ordered longitude/latitude bounds. Antimeridian wrapping is unsupported. |
| `near`, `radius_m` | Optional `longitude,latitude` in WGS84 and an integer radius of 1–50000 metres; both or neither. Cannot be combined with `bbox`. |

There is no pagination or result cap: `metadata.complete` is always `true` and
`total` equals the feature count. `mapped + unmapped = total`. Without `bbox`,
`scope` is `city` and features without coordinates remain available for the list.
With `bbox`, `scope` is `bbox` and only points within the inclusive bounds are
returned; unknown coordinates cannot be asserted inside the box. Analysis callers
must omit `bbox` to obtain the complete selected city, independently of map view.
With `near` and `radius_m`, `scope` is `radius` and only points whose straight-line
(spheroid) distance from `near` is at most `radius_m` are returned. The same
coordinate validity rules as `bbox` apply, so unlocated objects and seats without
reviewed geocoding are excluded. Each feature then carries
`properties.distance_m`, rounded to whole metres; it is null without `near`.
Distance is not walking or travel time. Results are ordered nearest first; equal distances fall back to name ordering.
Unsupported query parameters, repeated parameters and invalid filters return
HTTP 422 with `{"error":"invalid_query"}`. Database unavailable returns HTTP 503
with `{"error":"locations_unavailable"}`; internal exception text is never sent.

Each active facility appears once by canonical location ID even when multiple
sources attest it. An institution seat appears only when the institution has no
active facility, even if that facility is outside the requested city or box.
Seat IDs use `seat:<kindergarten_id>` and `location_id` is null. A seat has
point geometry only when its address has reviewed geocoding with an accepted,
active source record belonging to the same institution. Its role remains `seat`:
a legal seat is not treated as a confirmed service location. The card labels it
“Sjedište”. Geography is hidden if the current seat address differs from the
geocoded address or its geographic source is disabled/replaced. An unlocated active
facility also has null geometry but retains its facility ID and role. Sources
include the active records' reference date (null when unknown), fetch timestamp,
source URL/title and license (null when unrecorded). No missing coordinates,
reference dates or licenses are inferred. Current program/age evidence and
suitability counts are no longer returned. Retired age/program query parameters
are rejected with HTTP 422; historical programs remain dated evidence below.

`properties.historical_data` contains accepted records from active, approved
historical snapshots. Each item includes `reference_date`, `date_kind` (`published`
or `observed`), `scope`, `programs` (source labels), `vacancies` (age label, program
label and nullable nonnegative `free_places`), `source_title`, `source_url` and
`license`. Zero means a published zero; null means no count was published.
Facility records apply only to that exact object; institution records can appear
on its branches but their counts describe the whole institution, so never sum them
across branches. Historical data never confirms current age/program suitability.
The dedicated `kidsic-sync-historical` command and migration `0007` populate this
field from the pinned 2019/2025 Zagreb resources; other cities return an empty list.

`properties.field_sources` separately attributes stored fields to their accepted,
still import-approved dated evidence. It defaults to `{}`
and may contain `name`, `provider_kind`, `location_name`, `address`, `district`,
`quarter`, `suburb`, `neighbourhood`, `settlement`, `longitude` and `latitude`. Each entry contains the same source metadata as above
plus the compatibility flag `active_snapshot`, which is true for current-state
imports. Each source retains one current set of records; missing values supplied
by that source become unknown while evidence from other sources is preserved.
Missing field provenance remains absent, rather than assigning it to a
current source. Provenance must resolve to an accepted record of the same owner;
facility-specific fields additionally require the same location. If recorded
coordinate provenance is rejected, disabled, missing or points to another
owner/location, geometry becomes null and the location is excluded from `bbox`
results, while its list entry remains. Legacy/manual coordinates without recorded
field provenance remain available without an invented field source.

`properties.areas` lists the current attested district, quarter, suburb,
neighbourhood and non-city settlement names used by `area`. Names are not inferred
from addresses, institution names or coordinates. The list is empty when no area
is known. Recorded field evidence must be accepted, import-approved, active and
belong to the exact institution and location. Reviewed legacy/manual fields
without field provenance follow the existing read convention; no source is
invented. Historical `district` may remain visible with its field-source date,
but does not participate in `areas` or area filtering. Seat areas additionally
require the current-address check in `kindergarten_seat_geography`.

An area filter excludes unknown areas, including unlocated objects unless their
area is independently known. Known areas do not require coordinates. No geographic
boundary query is performed, and OSM labels are not asserted to be official
administrative boundaries. Coverage is incomplete; zero results means no attested
match, not that the area has no kindergartens. `metadata.complete` describes the
complete result set of the applied filters, not complete area coverage.

Properties also include nullable `website_url`, `email` and `phone`. Published
contacts in an accepted, active record for that exact facility take precedence;
a reviewed facility phone and institution contacts provide the fallback. A seat
uses institution contacts. Empty contact strings become null. The detail card
shows available contacts and keeps source records out of its visual content;
source metadata remains in the API response.

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
      "website_url": null, "email": null, "phone": null,
      "district": null, "location_role": "facility", "age_groups": null,
      "field_sources": {},
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

Run after setting `DATABASE_URL` and applying existing migrations:

```sh
uv sync --locked
uv run uvicorn KIDSic.api.locations:create_app --factory --host 127.0.0.1 --port 8000
curl 'http://127.0.0.1:8000/api/locations?city=Zagreb&provider_kind=municipal'
```

A missing/invalid database setting or unreachable database during pool startup
fails server startup clearly. Once started, database query/connection failures
return the sanitized HTTP 503 above. The server never runs migrations. Development
frontend traffic uses the Vite `/api` proxy; no permissive CORS policy is needed.

## Gradsko sufinanciranje u detaljima

`properties.subsidy_policies` sadrži aktualna pravila za grad fizičkog objekta
i `provider_kind` ustanove. Sjedište se koristi samo za rezultat vrste `seat`.
Nepoznati i ostali pružatelji ne nasljeđuju pravila gradskih vrtića. Pravila izvan
razdoblja važenja i ona provjerena tek u budućnosti ne vraćaju se.

Svako pravilo sadrži sažetak, razdoblje i datum provjere, službene poveznice,
`rates`, `conditions`, `reliefs` i `notes`. `amount_kind` razlikuje gradski udio
od roditeljske cijene; novčane vrijednosti u tarifama izražene su u eurocentima
mjesečno po djetetu. Status `partial` ne znači besplatnu uslugu. Predložene
promjene ne postaju važeće tarife. Pravilo ne potvrđuje individualno pravo ili
ugovor konkretne ustanove s Gradom. Prazna lista znači da podatak nije potvrđen.

Potrebna je migracija `0006_municipal_subsidies` i primjena provjerene snimke
iz [uputa za podatke](src/KIDSic/db/seeds/README.md). Isti odgovor koristi se
u web aplikaciji i MCP kartici; obje prikazuju odjeljak „Gradsko sufinanciranje”.

## Upis u detaljima

`properties.enrolment` sadrži objavljene krugove upisa ustanove: `round`
(`main` za glavni rok, `rolling` za upis tijekom pedagoške godine),
`academic_year`, `channel` (`city_system`, `e_upisi` ili `kindergarten`),
`application_url`, `opens_at` i `closes_at` (s vremenskom zonom), `accepting`,
izvor (`source_title`, `source_url`, `license`) te `reference_date` i `date_kind`
(`published` ili `observed`).

`status` se računa pri svakom čitanju iz objavljenih vremena: `upcoming`, `open`,
`closed`, `not_accepting` ili `dates_unknown`. Glavni rok bez objavljenog početka
nije `open`. Ako izvor kaže da ustanova za neku godinu ne provodi upise, ostali
krugovi te godine se ne vraćaju. Status nikad ne znači slobodno mjesto ni upis.

Krugovi dolaze iz pregledane snimke (`kidsic-sync-enrolment`, migracija
`0008_enrolment_rounds`) i vrijede samo za ustanove kojima su dodijeljeni;
gradski redovi bez ustanove se ne čitaju, jer bi došli i do privatnih vrtića.
Koraci i popis dokumenata nisu u ovom odgovoru: ostaju u citiranom izvoru i RAG
odlomcima teme `document`, kako bi isti tekst postojao samo jednom. Prazna
lista znači da kanal upisa nije potvrđen. Za Zagreb odgovor tako ostaje oko
121 KB komprimirano u MCP rezultatu (lokalna snimka, 461 objekt).
