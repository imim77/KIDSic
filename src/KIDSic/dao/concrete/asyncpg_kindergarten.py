"""PostgreSQL implementation of kindergarten search and RAG retrieval."""
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
