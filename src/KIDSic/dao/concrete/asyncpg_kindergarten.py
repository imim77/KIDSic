"""PostgreSQL implementation of kindergarten search and RAG retrieval."""
import math

import asyncpg

from KIDSic.dao.interfaces.kindergarten import KindergartenRepository
from KIDSic.dto.text import normalize


class AsyncpgKindergartenRepository(KindergartenRepository):
    def __init__(self, connection: asyncpg.Connection):
        self._connection = connection

    async def list_cities(self):
        return await self._connection.fetch('SELECT DISTINCT city_key,city_aliases FROM location')

    async def find_options(self, *, city: str, age_months: int, as_of=None,
                           include_unknown: bool = False, limit: int = 50):
        if not isinstance(age_months, int) or isinstance(age_months, bool) or not 0 <= age_months <= 216:
            raise ValueError('Dob mora biti broj mjeseci od 0 do 216.')
        if not city.strip() or not 1 <= limit <= 100:
            raise ValueError('Potreban je grad i limit od 1 do 100.')
        return await self._connection.fetch('''
          WITH valid_program AS (
            SELECT p.*,r.location_id AS evidence_location,s.url,s.title AS source_title
            FROM program p JOIN source_record r ON r.id=p.source_record_id
            JOIN data_source s ON s.id=r.source_id
            WHERE r.match_status='accepted' AND r.kindergarten_id=p.kindergarten_id
              AND s.import_allowed AND s.active_batch_id=r.batch_id
              AND p.verified_on<=COALESCE($3::date,CURRENT_DATE)
              AND (p.valid_until IS NULL OR p.valid_until>=COALESCE($3::date,CURRENT_DATE))
              AND (s.stale_after_days IS NULL OR p.verified_on>=COALESCE($3::date,CURRENT_DATE)-s.stale_after_days)
          ), candidates AS (
            SELECT l.id AS location_id,l.kindergarten_id,k.name,l.name AS location_name,l.city,l.address,
              COALESCE((SELECT jsonb_agg(jsonb_build_object(
                'program_id',p.id,'program_name',p.name,'source_record_id',p.source_record_id,
                'source_url',p.url,'source_title',p.source_title,'verified_on',p.verified_on,
                'scope',CASE WHEN p.location_id IS NULL THEN 'institution' ELSE 'location' END))
                FROM valid_program p WHERE p.kindergarten_id=k.id
                  AND (p.location_id IS NULL OR p.location_id=l.id)
                  AND (p.evidence_location IS NULL OR p.evidence_location=l.id)
                  AND p.min_age_months<=$2 AND $2<p.max_age_months_exclusive),'[]'::jsonb) AS age_evidence,
              EXISTS (SELECT 1 FROM valid_program p WHERE p.kindergarten_id=k.id
                  AND (p.location_id IS NULL OR p.location_id=l.id)
                  AND (p.evidence_location IS NULL OR p.evidence_location=l.id)
                  AND p.min_age_months IS NOT NULL AND p.max_age_months_exclusive IS NOT NULL
              ) AS has_known_program
            FROM location l JOIN kindergarten k ON k.id=l.kindergarten_id
            WHERE (l.city_key=$1 OR $1=ANY(l.city_aliases))
              AND EXISTS (SELECT 1 FROM source_record r JOIN data_source s ON s.id=r.source_id
                WHERE r.kindergarten_id=k.id AND (r.location_id IS NULL OR r.location_id=l.id)
                  AND r.match_status='accepted' AND s.import_allowed AND s.active_batch_id=r.batch_id)
          ) SELECT location_id,kindergarten_id,name,location_name,city,address,age_evidence,
                   CASE WHEN jsonb_array_length(age_evidence)>0 THEN 'confirmed' ELSE 'unknown' END AS age_status
            FROM candidates WHERE jsonb_array_length(age_evidence)>0 OR ($4 AND NOT has_known_program)
            ORDER BY jsonb_array_length(age_evidence)>0 DESC,name,location_id LIMIT $5
        ''', normalize(city), age_months, as_of, include_unknown, limit)


    async def retrieve_context(self, *, location_ids, text: str = '', embedding=None,
                               embedding_model: str | None = None, program_ids=(), limit: int = 8):
        if not 1 <= limit <= 30:
            raise ValueError('Limit mora biti od 1 do 30.')
        vector = None
        if embedding is not None:
            if not embedding_model or len(embedding) != 384 or not all(math.isfinite(float(x)) for x in embedding) or not any(embedding):
                raise ValueError('Potreban je model i konačan nenulti vektor dimenzije 384.')
            vector = '[' + ','.join(str(float(x)) for x in embedding) + ']'
        # Exact cosine ranking AFTER scope/source filtering: no ANN post-filter recall loss.
        return await self._connection.fetch('''
          SELECT c.id,c.kindergarten_id,c.location_id,c.content,c.source_url,c.source_record_id,
                 r.observed_on,r.fetched_at,s.title AS source_title,
                 CASE WHEN $3::vector IS NULL THEN NULL ELSE c.embedding <=> $3::vector END AS distance
          FROM knowledge_chunk c
          JOIN source_record r ON r.id=c.source_record_id
          JOIN data_source s ON s.id=r.source_id
          WHERE r.match_status='accepted' AND s.import_allowed AND s.active_batch_id=r.batch_id
            AND r.kindergarten_id=c.kindergarten_id
            AND (r.location_id IS NULL OR r.location_id IS NOT DISTINCT FROM c.location_id)
            AND EXISTS (SELECT 1 FROM location l WHERE l.id=ANY($1::uuid[])
              AND l.kindergarten_id=c.kindergarten_id AND (c.location_id IS NULL OR c.location_id=l.id))
            AND (c.program_id IS NULL OR (c.program_id=ANY($6::uuid[]) AND EXISTS (
              SELECT 1 FROM program p WHERE p.id=c.program_id
                AND (p.location_id IS NULL OR p.location_id=c.location_id))))
            AND ($3::vector IS NULL OR (c.embedding IS NOT NULL AND c.embedding_model=$4))
            AND ($3::vector IS NOT NULL OR c.search_text @@ websearch_to_tsquery('simple',$2))
          ORDER BY CASE WHEN $3::vector IS NOT NULL THEN c.embedding <=> $3::vector END,
                   ts_rank(c.search_text,websearch_to_tsquery('simple',$2)) DESC,c.id LIMIT $5
        ''', list(location_ids), text, vector, embedding_model, limit, list(program_ids))
