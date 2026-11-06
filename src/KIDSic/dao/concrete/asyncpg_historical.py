"""AsyncpgHistoricalRepository attaches history without creating current objects."""
import re
from uuid import uuid4

from KIDSic.dao.concrete.source_state import SourceStateWriter
from KIDSic.dao.interfaces.historical import HistoricalRepository
from KIDSic.dto.historical import HistoricalSnapshot
from KIDSic.dto.source import name_key
from KIDSic.exceptions import SourceImportError


def address_key(value: str) -> str:
    return ' '.join(re.sub(r'\b(?:ulica|ul)\b', '', name_key(value)).split())


class AsyncpgHistoricalRepository(HistoricalRepository):
    def __init__(self, connection):
        self._connection = connection

    async def import_snapshot(self, snapshot: HistoricalSnapshot) -> dict:
        SourceStateWriter.validate(row.source_key for row in snapshot.rows)
        async with self._connection.transaction():
            await self._connection.execute('SELECT pg_advisory_xact_lock(194733, 1)')
            return await self._import_snapshot(snapshot)

    async def _import_snapshot(self, snapshot):
        stored = await self._connection.fetchrow(
            'SELECT id,import_allowed FROM data_source WHERE dataset_key=$1 FOR UPDATE',
            snapshot.source.definition.key)
        if stored is None or not stored['import_allowed']:
            raise SourceImportError('Historical source must be registered and approved.')
        if not snapshot.rows:
            raise SourceImportError('Historical snapshot must not be empty.')
        # Only active, approved directory records can anchor a historical match.
        places = await self._connection.fetch('''
          WITH active AS (
            SELECT r.kindergarten_id,r.location_id FROM source_record r
            JOIN data_source s ON s.id=r.source_id AND s.active_batch_id=r.batch_id
            WHERE s.import_allowed AND r.match_status='accepted'
          )
          SELECT k.id,k.name,k.provider_kind,l.id AS location_id,l.address
          FROM kindergarten k LEFT JOIN location l ON l.kindergarten_id=k.id
            AND EXISTS(SELECT 1 FROM active a WHERE a.location_id=l.id AND a.kindergarten_id=k.id)
          LEFT JOIN municipality lm ON lm.id=l.municipality_id
          LEFT JOIN kindergarten_seat ks ON ks.kindergarten_id=k.id
          LEFT JOIN municipality km ON km.id=ks.municipality_id
          WHERE EXISTS(SELECT 1 FROM active a WHERE a.kindergarten_id=k.id)
            AND (lm.key='zagreb' OR (l.id IS NULL AND km.key='zagreb'))
        ''')
        accepted, batch = 0, uuid4()
        for row in snapshot.rows:
            matches = [p for p in places if name_key(p['name']) == name_key(row.name)
                and (row.provider_kind == 'unknown' or p['provider_kind'] == row.provider_kind)
                and (row.scope == 'institution' or (p['location_id'] is not None
                    and address_key(p['address'] or '') == address_key(row.address or '')))]
            identities = {(p['id'], p['location_id'] if row.scope == 'facility' else None) for p in matches}
            owner, location = next(iter(identities)) if len(identities) == 1 else (None, None)
            status = 'accepted' if owner is not None else 'candidate'
            accepted += status == 'accepted'
            await self._connection.execute('''INSERT INTO historical_record
                (source_id,batch_id,source_key,raw_data,kindergarten_id,location_id,scope,
                 match_status,reference_date,date_kind,fetched_at,programs,vacancies)
                VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)''',
                stored['id'], batch, row.source_key, row.raw_data, owner, location, row.scope,
                status, snapshot.reference_date, snapshot.date_kind, snapshot.fetched_at,
                list(row.programs), [v.model_dump(mode='json') for v in row.vacancies])
        if not accepted:
            raise SourceImportError('No historical records could be linked; retain the previous batch.')
        await SourceStateWriter.activate(self._connection, stored['id'], batch, snapshot.fetched_at,
            snapshot.reference_date if snapshot.date_kind == 'observed' else None)
        return {'source': snapshot.source.definition.key, 'records': len(snapshot.rows),
                'accepted': accepted, 'needs_review': len(snapshot.rows) - accepted,
                'reference_date': snapshot.reference_date.isoformat()}
