"""reviewed_snapshot holds the steps every reviewed-snapshot import repeats.

Each import reads one local, manually reviewed file (never the network) and
writes a new batch of its sources inside a single transaction, so a failed
import leaves the previous batch visible.
"""
import argparse
import asyncio
from datetime import datetime
import hashlib
import json
import uuid

from KIDSic.db.database import database_pool
from KIDSic.dao.concrete.source_state import SourceStateWriter
from KIDSic.dto.text import normalize

AREAS = ('quarter', 'suburb', 'neighbourhood')
OSM_COPYRIGHT = 'https://www.openstreetmap.org/copyright'


def run(doc, data_file, apply):
    """run applies a snapshot; without --apply it rolls back, so a dry run checks the same path."""
    parser = argparse.ArgumentParser(description=doc)
    parser.add_argument('--apply', action='store_true', help='Commit the import to DATABASE_URL.')
    commit = parser.parse_args().apply
    data = json.loads(data_file.read_text())

    async def main():
        async with database_pool() as pool, pool.acquire() as connection:
            transaction = connection.transaction()
            await transaction.start()
            try:
                result = await apply(connection, data)
            except BaseException:
                await transaction.rollback()
                raise
            await (transaction.commit() if commit else transaction.rollback())
            return result

    print(json.dumps(asyncio.run(main()), ensure_ascii=False))
    if not commit:
        print('Dry run: nothing was written. Repeat with --apply.')


def area_attributes(geo, existing):
    """area_attributes takes OSM areas, letting explicit user corrections win."""
    manual = (existing or {}).get('manual_area', {})
    attributes = {key: geo.get(key) for key in AREAS}
    attributes.update({key: manual[key] for key in AREAS if key in manual})
    return attributes, manual


class Batch:
    """Batch writes one reviewed snapshot: its sources, records, evidence and chunks.

    Create it with `Batch.start`, which takes the lock CKAN imports also use.
    """

    def __init__(self, connection, fetched_at):
        self._connection = connection
        self.id = uuid.uuid4()
        self._states = {}
        self.fetched_at = datetime.fromisoformat(fetched_at)

    @classmethod
    async def start(cls, connection, fetched_at):
        await connection.execute('SELECT pg_advisory_xact_lock(194733, 1)')
        return cls(connection, fetched_at)

    async def source(self, key, title, publisher, url, license, metadata):
        """source activates this batch for a data source; a revoked source stops the import."""
        stored = await self._connection.fetchrow('''
            INSERT INTO data_source(dataset_key,title,publisher,url,license,import_allowed,
                                    active_batch_id,fetched_at,metadata)
            VALUES ($1,$2,$3,$4,$5,true,$6,$7,$8)
            ON CONFLICT(dataset_key) DO UPDATE SET
                metadata=data_source.metadata || EXCLUDED.metadata
            RETURNING id,import_allowed
        ''', key, title, publisher, url, license, self.id, self.fetched_at, metadata)
        if not stored['import_allowed']:
            raise ValueError(f'Import is disabled for {key}.')
        self._states[stored['id']] = SourceStateWriter(
            self._connection, stored['id'], self.fetched_at, batch=self.id)
        return stored['id']

    async def record(self, source, key, raw, owner, location=None, status='accepted', note=None):
        record = await self._states[source].record(key, raw, owner=owner, location=location,
                                                   status=status, note=note)
        await self._states[source].clear_derived([record])
        return record

    async def finish(self):
        for state in self._states.values():
            await state.finish()

    async def evidence(self, location, record, fields, manual=()):
        """evidence links location fields to a record; user-corrected fields keep their own."""
        await self._connection.execute('UPDATE location SET provenance=provenance || $2 WHERE id=$1',
            location, {field: {'source_record_id': str(record)} for field in fields if field not in manual})

    async def chunk(self, owner, location, record, content, url):
        await self._connection.execute('''
            INSERT INTO knowledge_chunk(kindergarten_id,location_id,source_record_id,
                                        ordinal,content,source_url,content_sha256)
            VALUES ($1,$2,$3,0,$4,$5,$6)
        ''', owner, location, record, content, url, hashlib.sha256(content.encode()).hexdigest())

    async def location(self, location, owner, name, address, settlement, municipality, lon, lat, attributes):
        """location upserts a reviewed facility under a stable ID, merging attributes."""
        await self._connection.execute('''
            INSERT INTO location(id,kindergarten_id,name,address,settlement,settlement_key,
                                 municipality_id,longitude,latitude,attributes)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            ON CONFLICT(id) DO UPDATE SET name=EXCLUDED.name,address=EXCLUDED.address,
                settlement=EXCLUDED.settlement,settlement_key=EXCLUDED.settlement_key,
                municipality_id=EXCLUDED.municipality_id,longitude=EXCLUDED.longitude,
                latitude=EXCLUDED.latitude,attributes=location.attributes || EXCLUDED.attributes
        ''', location, owner, name, address, settlement, normalize(settlement), municipality, lon, lat, attributes)
