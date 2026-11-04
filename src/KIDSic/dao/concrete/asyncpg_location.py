"""AsyncpgLocationRepository reads active locations and source evidence together."""
from KIDSic.dao.interfaces.location import LocationRepository
from KIDSic.dto.location import LocationQuery
from KIDSic.dto.municipality import supported_city_key
from KIDSic.dto.text import normalize


class AsyncpgLocationRepository(LocationRepository):
    def __init__(self, connection):
        self._connection = connection

    async def list_locations(self, query: LocationQuery):
        return await self._connection.fetch('''
          WITH approved_record AS (
            SELECT r.id::text AS record_id,r.kindergarten_id,r.location_id,r.raw_data,r.fetched_at,
              COALESCE(s.active_batch_id=r.batch_id,false) AS active_snapshot,
              jsonb_build_object('name',s.title,'url',s.url,'license',s.license,
                'reference_date',r.observed_on,'retrieved_at',r.fetched_at) AS evidence
            FROM source_record r JOIN data_source s ON s.id=r.source_id
            WHERE r.match_status='accepted' AND s.import_allowed
          ), active_record AS (
            SELECT * FROM approved_record WHERE active_snapshot
          ), place AS (
            SELECT l.id AS location_id,l.kindergarten_id,l.name AS location_name,
              l.address,l.settlement,l.settlement_key,l.municipality_id,l.district,
              l.longitude,l.latitude,'facility' AS location_role,l.provenance AS field_provenance,
              l.attributes->>'phone' AS facility_phone,
              jsonb_build_object('district',l.district,'quarter',l.attributes->>'quarter',
                'suburb',l.attributes->>'suburb','neighbourhood',l.attributes->>'neighbourhood',
                'settlement',l.settlement) AS area_values,
              (SELECT jsonb_agg(DISTINCT r.evidence ORDER BY r.evidence)
               FROM active_record r WHERE r.location_id=l.id) AS sources
            FROM location l
            WHERE EXISTS (SELECT 1 FROM active_record r WHERE r.location_id=l.id)
            UNION ALL
            SELECT NULL,k.id,k.name,k.seat_address,k.seat_settlement,
              k.seat_settlement_key,k.seat_municipality_id,NULL,sg.longitude,sg.latitude,'seat',
              jsonb_build_object('location_name',k.provenance->'name',
                'address',k.provenance->'seat_address',
                'longitude',k.provenance->'seat_geography','latitude',k.provenance->'seat_geography',
                'quarter',k.provenance->'seat_geography','suburb',k.provenance->'seat_geography',
                'neighbourhood',k.provenance->'seat_geography','settlement',k.provenance->'seat_geography'),NULL,
              jsonb_build_object('quarter',sg.quarter,'suburb',sg.suburb,
                'neighbourhood',sg.neighbourhood,'settlement',sg.geo_settlement),
              (SELECT jsonb_agg(DISTINCT r.evidence ORDER BY r.evidence)
               FROM active_record r WHERE r.kindergarten_id=k.id)
            FROM kindergarten k LEFT JOIN kindergarten_seat_geography sg ON sg.kindergarten_id=k.id
            WHERE k.seat_settlement_key IS NOT NULL
              AND EXISTS (SELECT 1 FROM active_record r WHERE r.kindergarten_id=k.id)
              -- A facility outside the requested bounds still rules out a seat.
              AND NOT EXISTS (SELECT 1 FROM location l JOIN active_record r
                ON r.location_id=l.id WHERE l.kindergarten_id=k.id)
          ), candidate AS (
          SELECT pl.location_id,pl.kindergarten_id,k.name,pl.location_name,
            pl.address,pl.settlement AS city,k.provider_kind,pl.district,
            COALESCE(areas.names,'[]'::jsonb) AS areas,
            COALESCE(NULLIF(btrim(contact.raw_data->>'Web'),''),NULLIF(btrim(k.website_url),'')) AS website_url,
            COALESCE(NULLIF(btrim(contact.raw_data->>'Email'),''),NULLIF(btrim(k.email),'')) AS email,
            COALESCE(NULLIF(btrim(contact.raw_data->>'Telefon'),''),NULLIF(btrim(pl.facility_phone),''),
                     NULLIF(btrim(k.phone),'')) AS phone,
            pl.longitude,pl.latitude,pl.location_role,pl.sources,
            COALESCE(fields.field_sources,'{}') AS field_sources,
            COALESCE((SELECT jsonb_agg(to_jsonb(p) ORDER BY p.valid_from DESC,p.policy_key)
              FROM municipality_subsidy_policy p
              WHERE p.municipality_id=pl.municipality_id
                AND k.provider_kind=ANY(p.provider_kinds)
                AND p.verified_on<=CURRENT_DATE
                AND (p.valid_from IS NULL OR p.valid_from<=CURRENT_DATE)
                AND (p.valid_until IS NULL OR p.valid_until>=CURRENT_DATE)), '[]'::jsonb)
              AS subsidy_policies,
            NOT ((pl.field_provenance ? 'longitude' AND NOT
                  COALESCE(fields.field_sources ? 'longitude',false)) OR
                 (pl.field_provenance ? 'latitude' AND NOT
                  COALESCE(fields.field_sources ? 'latitude',false))) AS geometry_valid
          FROM place pl JOIN kindergarten k ON k.id=pl.kindergarten_id
          LEFT JOIN municipality m ON m.id=pl.municipality_id
          -- Area filters use current attestation; historical labels stay in district only.
          LEFT JOIN LATERAL (
            SELECT jsonb_agg(DISTINCT btrim(area.value) ORDER BY btrim(area.value)) AS names
            FROM jsonb_each_text(pl.area_values) area
            WHERE NULLIF(btrim(area.value),'') IS NOT NULL
              AND (area.key<>'settlement' OR (
                translate(lower(btrim(area.value)),'čćžšđ','cczsd')<>$1
                AND lower(btrim(area.value)) IS DISTINCT FROM lower(m.name)))
              AND (NOT (pl.field_provenance ? area.key) OR EXISTS (
                SELECT 1 FROM active_record r
                WHERE r.record_id=pl.field_provenance->area.key->>'source_record_id'
                  AND r.kindergarten_id=pl.kindergarten_id
                  AND r.location_id IS NOT DISTINCT FROM pl.location_id))
          ) areas ON true
          -- Published branch contacts take precedence over the institution fallback.
          LEFT JOIN LATERAL (
            SELECT r.raw_data FROM active_record r
            WHERE r.location_id=pl.location_id AND r.kindergarten_id=pl.kindergarten_id
              AND r.raw_data ?| ARRAY['Web','Email','Telefon']
            ORDER BY r.fetched_at DESC,r.record_id LIMIT 1
          ) contact ON true
          LEFT JOIN LATERAL (
            SELECT jsonb_object_agg(field.key,r.evidence ||
              jsonb_build_object('active_snapshot',r.active_snapshot)) AS field_sources
            FROM jsonb_each(pl.field_provenance || jsonb_build_object(
              'name',k.provenance->'name','provider_kind',k.provenance->'provider_kind')) field
            JOIN approved_record r ON r.record_id=field.value->>'source_record_id'
              AND r.kindergarten_id=pl.kindergarten_id
              AND (field.key IN ('name','provider_kind')
                OR (field.key='location_name' AND pl.location_role='seat')
                OR r.location_id IS NOT DISTINCT FROM pl.location_id)
            WHERE field.key IN ('name','provider_kind','location_name','address',
                                'district','quarter','suburb','neighbourhood','settlement',
                                'longitude','latitude')
          ) fields ON true
          WHERE (pl.settlement_key=$1 OR m.key=$1 OR $1=ANY(m.aliases))
            AND ($2='' OR strpos(translate(lower(k.name),'čćžšđ','cczsd'),$2)>0
                       OR strpos(translate(lower(pl.location_name),'čćžšđ','cczsd'),$2)>0)
            AND ($3::text IS NULL OR k.provider_kind=$3)
          )
          SELECT location_id,kindergarten_id,name,location_name,address,city,
            provider_kind,district,areas,website_url,email,phone,location_role,sources,field_sources,subsidy_policies,
            CASE WHEN geometry_valid THEN longitude END AS longitude,
            CASE WHEN geometry_valid THEN latitude END AS latitude
          FROM candidate
          WHERE ($4::float8[] IS NULL OR (
              geometry_valid AND longitude BETWEEN $4[1] AND $4[3]
              AND latitude BETWEEN $4[2] AND $4[4]))
            AND ($5='' OR EXISTS (SELECT 1 FROM jsonb_array_elements_text(areas) area(name)
              WHERE regexp_replace(translate(lower(btrim(area.name)),'čćžšđ','cczsd'),
                '^mjesni odbor ','')=$5))
          ORDER BY name,location_name,kindergarten_id,location_id
        ''', supported_city_key(query.city), normalize(query.q), query.provider_kind,
            list(query.bbox) if query.bbox is not None else None,
            normalize(query.area).removeprefix('mjesni odbor '))
