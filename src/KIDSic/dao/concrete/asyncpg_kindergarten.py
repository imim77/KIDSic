"""AsyncpgKindergartenRepository retrieves documents within accepted owner scopes."""
import asyncpg

from KIDSic.dao.interfaces.kindergarten import KindergartenRepository


class AsyncpgKindergartenRepository(KindergartenRepository):
    def __init__(self, connection: asyncpg.Connection):
        self._connection = connection

    async def retrieve_context(self, *, location_ids, kindergarten_ids=(), limit: int = 30):
        if type(limit) is not int or not 1 <= limit <= 30:
            raise ValueError('Limit mora biti od 1 do 30.')
        return await self._connection.fetch('''
          SELECT e.* FROM valid_knowledge_chunk e
          WHERE EXISTS (
            SELECT 1 FROM objekti l WHERE l.id=ANY($1::uuid[])
              AND l.kindergarten_id=e.kindergarten_id
              AND (e.location_id IS NULL OR e.location_id=l.id)
          )
          -- Seat-only results: institution-wide chunks, never another object's chunks.
          OR (e.location_id IS NULL AND e.kindergarten_id=ANY($2::uuid[]))
          ORDER BY e.id LIMIT $3
        ''', list(location_ids), list(kindergarten_ids), limit)
