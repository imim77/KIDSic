"""SourceStateWriter replaces source contents while preserving record identity."""
from uuid import uuid4

from KIDSic.exceptions import SourceImportError


class SourceStateWriter:
    # SourceStateWriter keeps replacement, dependency deletion and activation in
    # one caller-owned transaction; every import uses the same advisory lock.
    def __init__(self, connection, source_id, fetched_at, *, batch=None):
        self._connection = connection
        self.source_id = source_id
        self.fetched_at = fetched_at
        self.batch = batch or uuid4()
        self.keys = set()

    @staticmethod
    def validate(keys):
        keys = list(keys)
        if not keys or any(not key for key in keys) or len(set(keys)) != len(keys):
            raise SourceImportError('Source state must be nonempty with unique source_key values.')

    async def record(self, key, raw, *, owner=None, location=None, status='accepted',
                     method='manual', note=None, observed_on=None, record_id=None):
        if key in self.keys or not key:
            raise SourceImportError(f'Duplicate or empty source_key: {key!r}.')
        self.keys.add(key)
        return await self._connection.fetchval('''
            INSERT INTO source_record(id,source_id,batch_id,source_key,raw_data,fetched_at,
                observed_on,kindergarten_id,location_id,match_status,match_method,match_note)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
            ON CONFLICT (source_id,source_key) DO UPDATE SET
                batch_id=EXCLUDED.batch_id,raw_data=EXCLUDED.raw_data,
                fetched_at=EXCLUDED.fetched_at,observed_on=EXCLUDED.observed_on,
                kindergarten_id=CASE WHEN source_record.match_status='candidate'
                    THEN EXCLUDED.kindergarten_id ELSE source_record.kindergarten_id END,
                location_id=CASE WHEN source_record.match_status='candidate'
                    THEN EXCLUDED.location_id ELSE source_record.location_id END,
                match_status=CASE WHEN source_record.match_status='candidate'
                    THEN EXCLUDED.match_status ELSE source_record.match_status END,
                match_method=CASE WHEN source_record.match_status='candidate'
                    THEN EXCLUDED.match_method ELSE source_record.match_method END,
                match_note=CASE WHEN source_record.match_status='candidate'
                    THEN EXCLUDED.match_note ELSE source_record.match_note END
            RETURNING id
        ''', record_id or uuid4(), self.source_id, self.batch, key, raw, self.fetched_at,
            observed_on, owner, location, status, method, note)

    async def clear_derived(self, record_ids):
        await self._connection.execute('''DELETE FROM enrolment_refusal
            WHERE source_record_id=ANY($1::uuid[]) OR enrolment_id IN
              (SELECT id FROM enrolment WHERE source_record_id=ANY($1::uuid[]))''', list(record_ids))
        await self._connection.execute('''DELETE FROM knowledge_chunk WHERE program_id IN
            (SELECT id FROM program WHERE source_record_id=ANY($1::uuid[]))''', list(record_ids))
        for table in ('knowledge_chunk', 'enrolment', 'program'):
            await self._connection.execute(
                f'DELETE FROM {table} WHERE source_record_id=ANY($1::uuid[])', list(record_ids))

    async def finish(self, *, observed_on=None):
        self.validate(self.keys)
        missing = await self._connection.fetch('''
            SELECT id FROM source_record WHERE source_id=$1 AND NOT(source_key=ANY($2::text[]))
        ''', self.source_id, list(self.keys))
        ids = [r['id'] for r in missing]
        if ids:
            await self._forget_fields(ids)
            await self.clear_derived(ids)
            await self._connection.execute('DELETE FROM document_scope WHERE source_record_id=ANY($1::uuid[])', ids)
            await self._connection.execute('DELETE FROM source_record WHERE id=ANY($1::uuid[])', ids)
        await self.activate(self._connection, self.source_id, self.batch, self.fetched_at, observed_on)

    @staticmethod
    async def activate(connection, source, batch, fetched_at, observed_on=None):
        await connection.execute('''UPDATE data_source
            SET active_batch_id=$2,fetched_at=$3,observed_on=$4 WHERE id=$1''',
            source, batch, fetched_at, observed_on)

    async def _forget_fields(self, ids):
        texts = {str(value) for value in ids}
        for table in ('kindergarten', 'location'):
            rows = await self._connection.fetch(f'''SELECT * FROM {table} t WHERE EXISTS (
                SELECT 1 FROM jsonb_each(t.provenance) f
                WHERE f.value->>'source_record_id'=ANY($1::text[]))''', list(texts))
            for row in rows:
                provenance = dict(row['provenance'])
                removed = [key for key, value in provenance.items()
                           if value.get('source_record_id') in texts]
                if table == 'kindergarten' and set(removed) & {'name', 'provider_kind'}:
                    active = await self._connection.fetchval('''SELECT EXISTS (
                        SELECT 1 FROM source_record r JOIN data_source s ON s.id=r.source_id
                        WHERE r.kindergarten_id=$1 AND r.id<>ALL($2::uuid[])
                          AND r.match_status='accepted' AND s.import_allowed
                          AND (s.active_batch_id=r.batch_id OR r.batch_id=$3))''', row['id'], ids, self.batch)
                    if active and ('name' in removed or row['provider_kind'] != 'unknown'):
                        raise SourceImportError(f'Review classification before removing evidence: {row["name"]}.')
                values = {}
                attributes = dict(row.get('attributes') or {})
                for key in removed:
                    provenance.pop(key)
                    if key == 'seat_geography':
                        values.update(seat_longitude=None, seat_latitude=None, seat_attributes={})
                    if key in ('name', 'provider_kind', 'location_name', 'settlement'):
                        continue  # Inactive orphan identities may retain their display label.
                    if key in row and key not in ('id', 'kindergarten_id'):
                        values[key] = None
                    elif key in attributes:
                        attributes.pop(key)
                if table == 'location':
                    values['attributes'] = attributes
                values['provenance'] = provenance
                columns = ','.join(f'{key}=${index}' for index, key in enumerate(values, 2))
                await self._connection.execute(f'UPDATE {table} SET {columns} WHERE id=$1',
                                                row['id'], *values.values())
