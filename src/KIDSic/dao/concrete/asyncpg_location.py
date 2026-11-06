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
            SELECT r.id::text AS record_id,r.source_id,r.kindergarten_id,r.location_id,r.raw_data,r.fetched_at,
              COALESCE(s.active_batch_id=r.batch_id,false) AS active_snapshot,
              jsonb_build_object('name',s.title,'url',s.url,'license',s.license,
                'reference_date',r.observed_on,'retrieved_at',r.fetched_at) AS evidence
            FROM source_record r JOIN data_source s ON s.id=r.source_id
            WHERE r.match_status='accepted' AND s.import_allowed
          ), active_record AS (
            SELECT * FROM approved_record WHERE active_snapshot
          ), valid_program AS (
            SELECT p.*,r.location_id AS evidence_location,s.url AS source_url,
              s.title AS source_title
            FROM program p JOIN active_record r ON r.record_id=p.source_record_id::text
            JOIN data_source s ON s.id=r.source_id
            WHERE r.kindergarten_id=p.kindergarten_id
              AND p.verified_on<=CURRENT_DATE
              AND (p.valid_until IS NULL OR p.valid_until>=CURRENT_DATE)
              AND (s.stale_after_days IS NULL OR p.verified_on>=CURRENT_DATE-s.stale_after_days)
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
            COALESCE(program_data.programs,'[]'::jsonb) AS programs,
            COALESCE(history.records,'[]'::jsonb) AS historical_data,
            COALESCE(rounds.items,'[]'::jsonb) AS enrolment,
            CASE WHEN $6::int IS NULL AND $7='' THEN 'not_evaluated'
              WHEN program_data.matches THEN 'confirmed'
              WHEN program_data.programs IS NULL OR program_data.unknown_age THEN 'unknown'
              ELSE 'excluded' END AS suitability_status,
            COALESCE(NULLIF(btrim(contact.raw_data->>'Web'),''),NULLIF(btrim(k.website_url),'')) AS website_url,
            COALESCE(NULLIF(btrim(contact.raw_data->>'Email'),''),NULLIF(btrim(k.email),'')) AS email,
            COALESCE(NULLIF(btrim(contact.raw_data->>'Telefon'),''),NULLIF(btrim(pl.facility_phone),''),
                     NULLIF(btrim(k.phone),'')) AS phone,
            pl.longitude,pl.latitude,pl.location_role,pl.sources,
            COALESCE(fields.field_sources,'{}') AS field_sources,
            jsonb_build_object(
              'website_url',CASE WHEN NULLIF(btrim(contact.raw_data->>'Web'),'') IS NOT NULL
                THEN contact.evidence || '{"scope":"facility"}'::jsonb ELSE owner_contacts.evidence->'website_url' END,
              'email',CASE WHEN NULLIF(btrim(contact.raw_data->>'Email'),'') IS NOT NULL
                THEN contact.evidence || '{"scope":"facility"}'::jsonb ELSE owner_contacts.evidence->'email' END,
              'phone',CASE WHEN NULLIF(btrim(contact.raw_data->>'Telefon'),'') IS NOT NULL
                THEN contact.evidence || '{"scope":"facility"}'::jsonb
                WHEN NULLIF(btrim(pl.facility_phone),'') IS NULL THEN owner_contacts.evidence->'phone' END
            ) AS contact_sources,
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
          LEFT JOIN LATERAL (
            SELECT jsonb_agg(jsonb_build_object('reference_date',h.reference_date,
              'date_kind',h.date_kind,'scope',h.scope,'programs',h.programs,'vacancies',h.vacancies,
              'source_title',s.title,'source_url',COALESCE(s.metadata->>'resource_url',s.url),
              'license',s.license) ORDER BY h.reference_date DESC,s.dataset_key,h.source_key) AS records
            FROM historical_record h JOIN data_source s ON s.id=h.source_id
              AND s.active_batch_id=h.batch_id
            WHERE s.import_allowed AND h.match_status='accepted'
              AND h.kindergarten_id=pl.kindergarten_id
              AND ((h.scope='institution' AND h.location_id IS NULL)
                OR (h.scope='facility' AND h.location_id=pl.location_id))
              AND (cardinality(h.programs)>0 OR jsonb_array_length(h.vacancies)>0)
          ) history ON true
          -- Shared applicability enforces named owners and municipality/provider rules.
          LEFT JOIN LATERAL (
            SELECT jsonb_agg(jsonb_build_object('round',e.round,'academic_year',e.academic_year,
              'channel',e.channel,'application_url',e.application_url,'accepting',NOT EXISTS (
                SELECT 1 FROM enrolment_refusal f JOIN active_record fr
                  ON fr.record_id=f.source_record_id::text
                JOIN document_applicability fa ON fa.source_record_id=f.source_record_id
                  AND fa.kindergarten_id=pl.kindergarten_id
                WHERE f.enrolment_id=e.id AND f.kindergarten_id=pl.kindergarten_id),
              'opens_at',e.opens_at,'closes_at',e.closes_at,
              'source_title',s.title,'source_url',COALESCE(r.raw_data->>'document_url',s.url),'license',s.license,
              'reference_date',COALESCE(r.evidence->>'reference_date',r.raw_data->>'reference_date'),
              'date_kind',CASE WHEN r.evidence->>'reference_date' IS NOT NULL THEN 'observed'
                ELSE COALESCE(r.raw_data->>'date_kind','unknown') END)
              ORDER BY e.academic_year DESC,e.round,s.dataset_key) AS items
            FROM enrolment e JOIN active_record r ON r.record_id=e.source_record_id::text
            JOIN data_source s ON s.id=r.source_id
            JOIN document_applicability a ON a.source_record_id=e.source_record_id
            WHERE a.kindergarten_id=pl.kindergarten_id
          ) rounds ON true
          LEFT JOIN LATERAL (
            SELECT jsonb_agg(jsonb_build_object('program_id',p.id,'name',p.name,
              'min_age_months',p.min_age_months,'max_age_months_exclusive',p.max_age_months_exclusive,
              'verified_on',p.verified_on,'valid_until',p.valid_until,
              'source_record_id',p.source_record_id,'source_url',p.source_url,'source_title',p.source_title,
              'scope',CASE WHEN p.location_id IS NULL AND p.evidence_location IS NULL
                THEN 'institution' ELSE 'facility' END) ORDER BY p.name,p.id) AS programs,
              bool_or($6::int IS NULL OR (p.min_age_months<=$6 AND $6<p.max_age_months_exclusive)) AS matches,
              bool_or(p.min_age_months IS NULL OR p.max_age_months_exclusive IS NULL) AS unknown_age
            FROM valid_program p WHERE p.kindergarten_id=pl.kindergarten_id
              AND (p.location_id IS NULL OR p.location_id=pl.location_id)
              AND (p.evidence_location IS NULL OR p.evidence_location=pl.location_id)
              AND ($7='' OR strpos(translate(lower(p.name),'čćžšđ','cczsd'),$7)>0)
          ) program_data ON true
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
            SELECT r.raw_data,r.evidence FROM active_record r
            WHERE r.location_id=pl.location_id AND r.kindergarten_id=pl.kindergarten_id
              AND r.raw_data ?| ARRAY['Web','Email','Telefon']
            ORDER BY r.fetched_at DESC,r.record_id LIMIT 1
          ) contact ON true
          LEFT JOIN LATERAL (
            SELECT jsonb_object_agg(field.key,r.evidence || jsonb_build_object('scope',
              CASE WHEN r.location_id IS NULL THEN 'institution' ELSE 'facility' END)) AS evidence
            FROM jsonb_each(k.provenance) field JOIN active_record r
              ON r.record_id=field.value->>'source_record_id' AND r.kindergarten_id=k.id
                AND (r.location_id IS NULL OR r.location_id=pl.location_id)
            WHERE field.key IN ('website_url','email','phone')
          ) owner_contacts ON true
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
            provider_kind,district,areas,programs,historical_data,enrolment,suitability_status,
            website_url,email,phone,contact_sources,location_role,sources,field_sources,subsidy_policies,
            CASE WHEN geometry_valid THEN longitude END AS longitude,
            CASE WHEN geometry_valid THEN latitude END AS latitude,
            CASE WHEN $9::float8[] IS NOT NULL AND geometry_valid THEN round(ST_Distance(
              ST_MakePoint(longitude,latitude)::geography,
              ST_MakePoint($9[1],$9[2])::geography))::int END AS distance_m
          FROM candidate
          WHERE ($4::float8[] IS NULL OR (
              geometry_valid AND longitude BETWEEN $4[1] AND $4[3]
              AND latitude BETWEEN $4[2] AND $4[4]))
            -- Geography measures metres on the spheroid; NULL points never match.
            AND ($9::float8[] IS NULL OR (geometry_valid AND ST_DWithin(
              ST_MakePoint(longitude,latitude)::geography,
              ST_MakePoint($9[1],$9[2])::geography,$10::float8)))
            AND ($5='' OR EXISTS (SELECT 1 FROM jsonb_array_elements_text(areas) area(name)
              WHERE regexp_replace(translate(lower(btrim(area.name)),'čćžšđ','cczsd'),
                '^mjesni odbor ','')=$5))
            AND suitability_status<>'excluded'
            AND ($8::boolean OR suitability_status<>'unknown')
            -- Only the newest snapshot that publishes vacancies counts; an
            -- older positive count must not outlive a newer published zero.
            AND (NOT $11::boolean OR COALESCE((
              SELECT bool_or((v.item->>'free_places')::int>0)
              FROM (SELECT r.item FROM jsonb_array_elements(historical_data) r(item)
                    WHERE jsonb_array_length(r.item->'vacancies')>0
                    ORDER BY r.item->>'reference_date' DESC LIMIT 1) latest,
                jsonb_array_elements(latest.item->'vacancies') v(item)),false))
          -- Nearest first within each suitability group; distance is NULL without near.
          ORDER BY suitability_status='confirmed' DESC,distance_m NULLS LAST,
            name,location_name,kindergarten_id,location_id
        ''', supported_city_key(query.city), normalize(query.q), query.provider_kind,
            list(query.bbox) if query.bbox is not None else None,
            normalize(query.area).removeprefix('mjesni odbor '),
            query.age_months, normalize(query.program), query.include_unknown,
            list(query.near) if query.near is not None else None, query.radius_m,
            query.has_vacancies)
