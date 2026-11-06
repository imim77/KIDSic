"""PostgreSQL implementation of kindergarten search and RAG retrieval."""
import asyncpg

from KIDSic.dao.interfaces.kindergarten import KindergartenRepository
from KIDSic.dto.municipality import MUNICIPALITIES
from KIDSic.dto.text import normalize


class AsyncpgKindergartenRepository(KindergartenRepository):
    def __init__(self, connection: asyncpg.Connection):
        self._connection = connection

    async def list_cities(self):
        return await self._connection.fetch('''
            SELECT key AS city_key,aliases AS city_aliases FROM municipality
            WHERE key=ANY($1::text[])
        ''', list(MUNICIPALITIES))

    async def list_areas(self, *, city: str):
        return await self._connection.fetch('''
            SELECT DISTINCT area.name FROM location l
            LEFT JOIN municipality m ON m.id=l.municipality_id
            CROSS JOIN LATERAL (VALUES ('district',l.district),
                ('quarter',l.attributes->>'quarter'),('suburb',l.attributes->>'suburb'),
                ('neighbourhood',l.attributes->>'neighbourhood')) AS area(field,name)
            WHERE (l.settlement_key=$1 OR m.key=$1 OR $1=ANY(m.aliases))
              AND area.name IS NOT NULL
              AND (NOT (l.provenance ? area.field) OR EXISTS (
                SELECT 1 FROM source_record r JOIN data_source s ON s.id=r.source_id
                WHERE r.id::text=l.provenance->area.field->>'source_record_id'
                  AND r.location_id=l.id AND r.match_status='accepted'
                  AND s.import_allowed AND s.active_batch_id=r.batch_id))
              AND EXISTS (SELECT 1 FROM source_record r JOIN data_source s ON s.id=r.source_id
                WHERE r.location_id=l.id AND r.match_status='accepted'
                  AND s.import_allowed AND s.active_batch_id=r.batch_id)
            UNION
            SELECT DISTINCT area.name FROM kindergarten k
            JOIN kindergarten_seat_geography sg ON sg.kindergarten_id=k.id
            LEFT JOIN municipality m ON m.id=k.seat_municipality_id
            CROSS JOIN LATERAL unnest(ARRAY[sg.quarter,sg.suburb,sg.neighbourhood,sg.geo_settlement]) AS area(name)
            WHERE (k.seat_settlement_key=$1 OR m.key=$1 OR $1=ANY(m.aliases))
              AND area.name IS NOT NULL AND area.name IS DISTINCT FROM k.seat_settlement
              AND area.name IS DISTINCT FROM m.name
              AND NOT EXISTS (SELECT 1 FROM location l JOIN source_record r ON r.location_id=l.id
                JOIN data_source s ON s.id=r.source_id WHERE l.kindergarten_id=k.id
                  AND r.match_status='accepted' AND s.import_allowed AND s.active_batch_id=r.batch_id)
        ''', normalize(city))

    async def retrieve_context(self, *, location_ids, kindergarten_ids=(), limit: int = 30):
        if type(limit) is not int or not 1 <= limit <= 30:
            raise ValueError('Limit mora biti od 1 do 30.')
        return await self._connection.fetch('''
          SELECT c.id,a.kindergarten_id,c.location_id,c.content,c.source_url,c.source_record_id,
                 r.observed_on,r.fetched_at,s.title AS source_title,s.license,
                 -- Reviewed documents carry their own scope and governed period.
                 CASE WHEN r.raw_data->>'kind'='enrolment_document' THEN r.raw_data->>'scope' END AS document_scope,
                 CASE WHEN r.raw_data->>'kind'='enrolment_document' AND r.raw_data->>'date_kind'='published'
                   THEN (r.raw_data->>'reference_date')::date END AS published_on,
                 CASE WHEN r.raw_data->>'kind'='enrolment_document'
                   THEN (r.raw_data->>'valid_until')::date>=current_date END AS in_effect
          FROM knowledge_chunk c
          JOIN source_record r ON r.id=c.source_record_id
          JOIN document_applicability a ON a.source_record_id=r.id
          JOIN data_source s ON s.id=r.source_id
          WHERE r.match_status='accepted' AND s.import_allowed AND s.active_batch_id=r.batch_id
            AND r.kindergarten_id IS NOT DISTINCT FROM c.kindergarten_id
            AND (r.raw_data->>'evidence_scope' IS DISTINCT FROM 'registered_seat_geography'
              OR EXISTS (SELECT 1 FROM kindergarten_seat_geography sg
                WHERE sg.kindergarten_id=a.kindergarten_id AND sg.source_record_id=r.id))
            AND (r.location_id IS NULL OR r.location_id IS NOT DISTINCT FROM c.location_id)
            AND (EXISTS (SELECT 1 FROM location l WHERE l.id=ANY($1::uuid[])
              AND l.kindergarten_id=a.kindergarten_id AND (c.location_id IS NULL OR c.location_id=l.id))
              -- Seat-only results: institution-wide chunks, never another object's chunks.
              OR (c.location_id IS NULL AND a.kindergarten_id=ANY($2::uuid[])))
          ORDER BY c.id LIMIT $3
        ''', list(location_ids), list(kindergarten_ids), limit)
