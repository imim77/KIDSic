"""SourceStateWriter replaces source contents while preserving record identity."""
from uuid import uuid4

from KIDSic.exceptions import SourceImportError


class SourceStateWriter:
    # SourceStateWriter keeps replacement, dependency deletion and activation in
    # one caller-owned transaction; every import uses the same advisory lock.
    def __init__(self, connection, source_id, fetched_at):
        self._connection = connection
        self.source_id = source_id
        self.fetched_at = fetched_at
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
            INSERT INTO izvorni_zapisi(id,source_id,source_key,raw_data,fetched_at,
                observed_on,kindergarten_id,location_id,match_status,match_method,match_note)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            ON CONFLICT (source_id,source_key) DO UPDATE SET
                raw_data=EXCLUDED.raw_data,
                fetched_at=EXCLUDED.fetched_at,observed_on=EXCLUDED.observed_on,
                kindergarten_id=CASE WHEN izvorni_zapisi.match_status='candidate'
                    THEN EXCLUDED.kindergarten_id ELSE izvorni_zapisi.kindergarten_id END,
                location_id=CASE WHEN izvorni_zapisi.match_status='candidate'
                    THEN EXCLUDED.location_id ELSE izvorni_zapisi.location_id END,
                match_status=CASE WHEN izvorni_zapisi.match_status='candidate'
                    THEN EXCLUDED.match_status ELSE izvorni_zapisi.match_status END,
                match_method=CASE WHEN izvorni_zapisi.match_status='candidate'
                    THEN EXCLUDED.match_method ELSE izvorni_zapisi.match_method END,
                match_note=CASE WHEN izvorni_zapisi.match_status='candidate'
                    THEN EXCLUDED.match_note ELSE izvorni_zapisi.match_note END
            RETURNING id
        ''', record_id or uuid4(), self.source_id, key, raw, self.fetched_at,
            observed_on, owner, location, status, method, note)

    async def clear_derived(self, record_ids):
        # Reimports keep the source record, so its children need explicit cleanup.
        await self._connection.execute('''DELETE FROM neprihvacanja_upisa
            WHERE source_record_id=ANY($1::uuid[])''', list(record_ids))
        for table in ('odlomci_znanja', 'upisni_krugovi'):
            await self._connection.execute(
                f'DELETE FROM {table} WHERE source_record_id=ANY($1::uuid[])', list(record_ids))

    async def finish(self, *, observed_on=None):
        self.validate(self.keys)
        missing = await self._connection.fetch('''
            SELECT id FROM izvorni_zapisi WHERE source_id=$1 AND NOT(source_key=ANY($2::text[]))
        ''', self.source_id, list(self.keys))
        ids = [r['id'] for r in missing]
        if ids:
            await self._forget_fields(ids)
            await self._connection.execute('DELETE FROM izvorni_zapisi WHERE id=ANY($1::uuid[])', ids)
        await self.activate(self._connection, self.source_id, self.fetched_at, observed_on)

    @staticmethod
    async def activate(connection, source, fetched_at, observed_on=None):
        await connection.execute('''UPDATE izvori_podataka
            SET fetched_at=$2,observed_on=$3 WHERE id=$1''',
            source, fetched_at, observed_on)

    async def _forget_fields(self, ids):
        await self._connection.execute('''UPDATE sjedista_vrtica SET geography_source_record_id=NULL,
            longitude=NULL,latitude=NULL,attributes='{}' WHERE geography_source_record_id=ANY($1::uuid[])''', ids)
        texts = {str(value) for value in ids}
        for table in ('vrtici', 'objekti'):
            rows = await self._connection.fetch(f'''SELECT * FROM {table} t WHERE EXISTS (
                SELECT 1 FROM jsonb_each(t.provenance) f
                WHERE f.value->>'source_record_id'=ANY($1::text[]))''', list(texts))
            for row in rows:
                provenance = dict(row['provenance'])
                removed = [key for key, value in provenance.items()
                           if value.get('source_record_id') in texts]
                if table == 'vrtici' and set(removed) & {'name', 'provider_kind'}:
                    active = await self._connection.fetchval('''SELECT EXISTS (
                        SELECT 1 FROM izvorni_zapisi r JOIN izvori_podataka s ON s.id=r.source_id
                        WHERE r.kindergarten_id=$1 AND r.id<>ALL($2::uuid[])
                          AND r.match_status='accepted' AND s.import_allowed)''', row['id'], ids)
                    if active and ('name' in removed or row['provider_kind'] != 'unknown'):
                        raise SourceImportError(f'Review classification before removing evidence: {row["name"]}.')
                values = {}
                seat_values = {}
                attributes = dict(row.get('attributes') or {})
                for key in removed:
                    provenance.pop(key)
                    if table == 'vrtici' and key in {
                            'seat_address', 'seat_postal_code', 'seat_settlement',
                            'seat_settlement_key', 'seat_municipality_id'}:
                        seat_values[key.removeprefix('seat_')] = None
                    if key in ('name', 'provider_kind', 'location_name', 'settlement'):
                        continue  # Inactive orphan identities may retain their display label.
                    if table == 'objekti' and key == 'kind':
                        values[key] = 'unknown'  # Required classification loses its evidence.
                    elif key in row and key not in ('id', 'kindergarten_id'):
                        values[key] = None
                    elif key in attributes:
                        attributes.pop(key)
                if seat_values:
                    if 'settlement' in seat_values:
                        seat_values['settlement_key'] = None
                    columns = ','.join(f'{key}=${index}' for index,key in enumerate(seat_values,2))
                    await self._connection.execute(f'UPDATE sjedista_vrtica SET {columns} WHERE kindergarten_id=$1',
                                                   row['id'], *seat_values.values())
                if table == 'objekti':
                    values['attributes'] = attributes
                values['provenance'] = provenance
                columns = ','.join(f'{key}=${index}' for index, key in enumerate(values, 2))
                await self._connection.execute(f'UPDATE {table} SET {columns} WHERE id=$1',
                                                row['id'], *values.values())
