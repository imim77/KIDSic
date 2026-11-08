"""AsyncpgKindergartenRepository retrieves documents within accepted owner scopes."""
import asyncpg

from KIDSic.dao.interfaces.kindergarten import KindergartenRepository


class AsyncpgKindergartenRepository(KindergartenRepository):
    def __init__(self, connection: asyncpg.Connection):
        self._connection = connection

    async def retrieve_context(self, *, location_ids, kindergarten_ids=(), limit: int = 30):
        if type(limit) is not int or not 1 <= limit <= 30:
            raise ValueError('Limit mora biti od 1 do 30.')
        return await self._connection.fetch("""
          SELECT e.id,e.id_vrtica AS kindergarten_id,e.id_objekta AS location_id,e.sadrzaj AS content,e.poveznica_izvora AS source_url,e.id_izvornog_zapisa AS source_record_id,e.datum_opazanja AS observed_on,e.dohvaceno_u AS fetched_at,e.naslov_izvora AS source_title,e.licenca AS license,e.obuhvat_dokumenta AS document_scope,e.datum_objave AS published_on,e.na_snazi AS in_effect FROM valid_knowledge_chunk e
          WHERE EXISTS (
            SELECT 1 FROM objekti l WHERE l.id=ANY($1::uuid[])
              AND l.id_vrtica=e.id_vrtica
              AND (e.id_objekta IS NULL OR e.id_objekta=l.id)
          )
          -- Seat-only results: institution-wide chunks, never another object's chunks.
          OR (e.id_objekta IS NULL AND e.id_vrtica=ANY($2::uuid[]))
          ORDER BY e.id LIMIT $3
        """, list(location_ids), list(kindergarten_ids), limit)
