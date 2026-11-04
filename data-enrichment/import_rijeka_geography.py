"""Import reviewed Rijeka geography into existing CSV facilities without HTTP calls."""
import argparse
import asyncio
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import uuid

from KIDSic.db.database import database_pool

DATA_FILE = Path(__file__).with_name('rijeka-reviewed-geography.json')
_AREAS = ('quarter', 'suburb', 'neighbourhood')


class RijekaGeographyImporter:
    """RijekaGeographyImporter binds reviewed evidence to unchanged CSV identities."""
    def __init__(self, connection):
        self._connection = connection

    async def apply(self, data):
        accepted = [item for item in data['objects'] if item['review_status'] == 'matched']
        if not accepted:
            raise ValueError('No reviewed Rijeka locations; preserve the last good geography.')
        identities = set()
        for item in accepted:
            identity = uuid.UUID(item['location_id'])
            geo = item['selected']
            lon, lat = geo['longitude'], geo['latitude']
            if (identity in identities or not item.get('review_note') or not geo.get('source_url')
                    or not all(type(v) in (int, float) and math.isfinite(v) for v in (lon, lat))
                    or not (14.30 < lon < 14.56 and 45.28 < lat < 45.42)):
                raise ValueError('Invalid or duplicate reviewed Rijeka geography.')
            identities.add(identity)
        await self._connection.execute('SELECT pg_advisory_xact_lock(194733,1)')
        batch = uuid.uuid4()
        fetched_at = datetime.fromisoformat(data['fetched_at'])
        source = await self._connection.fetchrow('''
            INSERT INTO data_source(dataset_key,title,publisher,url,license,import_allowed,
                                    active_batch_id,fetched_at,metadata)
            VALUES ('rijeka-reviewed-geography','OpenStreetMap — riječke lokacije vrtića',
                    'OpenStreetMap contributors','https://www.openstreetmap.org/copyright',
                    $1,true,$2,$3,$4)
            ON CONFLICT(dataset_key) DO UPDATE SET active_batch_id=EXCLUDED.active_batch_id,
                fetched_at=EXCLUDED.fetched_at,metadata=data_source.metadata || EXCLUDED.metadata
            RETURNING id,import_allowed
        ''', data['licence'], batch, fetched_at,
            {'attribution': data['attribution'], 'cache_file': DATA_FILE.name})
        if not source['import_allowed']:
            raise ValueError('Import is disabled for reviewed Rijeka geography.')
        for item in accepted:
            location = uuid.UUID(item['location_id'])
            stored = await self._connection.fetchrow('''
                SELECT l.kindergarten_id,l.name,l.address,l.attributes
                FROM location l JOIN municipality m ON m.id=l.municipality_id
                WHERE l.id=$1 AND m.key='rijeka' AND EXISTS (
                    SELECT 1 FROM source_record r JOIN data_source s ON s.id=r.source_id
                    WHERE r.location_id=l.id AND r.kindergarten_id=l.kindergarten_id
                      AND s.dataset_key='rijeka-kindergartens' AND r.source_key=$2
                      AND s.import_allowed AND s.active_batch_id=r.batch_id
                      AND r.match_status='accepted') FOR UPDATE OF l
            ''', location, item['source_key'])
            if (stored is None or str(stored['kindergarten_id']) != item['kindergarten_id']
                    or stored['name'] != item['location_name'] or stored['address'] != item['address']):
                raise ValueError(f"Review the changed Rijeka location: {item['location_name']}")
            geo = item['selected']
            record = await self._connection.fetchval('''
                INSERT INTO source_record(source_id,batch_id,source_key,raw_data,fetched_at,
                                          kindergarten_id,location_id,match_status,match_method,match_note)
                VALUES ($1,$2,$3,$4,$5,$6,$7,'accepted','manual',$8) RETURNING id
            ''', source['id'], batch, item['source_key'], {**item, 'reviewed_address': item['address']},
                fetched_at, stored['kindergarten_id'], location, item['review_note'])
            manual = stored['attributes'].get('manual_area', {})
            attributes = {field: geo.get(field) for field in _AREAS}
            attributes.update({key: manual[key] for key in _AREAS if key in manual})
            attributes.update(geocoding_review_status='matched',
                              geocoding_match_basis=geo['match_basis'])
            fields = ('longitude', 'latitude', *_AREAS)
            provenance = {field: {'source_record_id': str(record)} for field in fields
                          if field not in manual and geo.get(field) is not None}
            await self._connection.execute('''
                UPDATE location SET longitude=$2,latitude=$3,
                    attributes=attributes || $4,provenance=provenance || $5 WHERE id=$1
            ''', location, geo['longitude'], geo['latitude'], attributes, provenance)
            areas = '; '.join(f'{key}: {attributes[key]}' for key in _AREAS if attributes.get(key))
            content = (f"{item['location_name']}. Adresa: {item['address']}, Rijeka. "
                       f"{areas}. Koordinate: {geo['latitude']}, {geo['longitude']}. "
                       f"Podloga podudaranja: {geo['match_basis']}. "
                       f"OSM područja nisu potvrda službenih gradskih granica. "
                       f"{data['attribution']}; {data['licence']}.")
            await self._connection.execute('''
                INSERT INTO knowledge_chunk(kindergarten_id,location_id,source_record_id,
                                            ordinal,content,source_url,content_sha256)
                VALUES ($1,$2,$3,0,$4,$5,$6)
            ''', stored['kindergarten_id'], location, record, content, geo['source_url'],
                hashlib.sha256(content.encode()).hexdigest())
        return {'imported': len(accepted), 'needs_review': len(data['objects']) - len(accepted)}


async def import_geography(data):
    async with database_pool() as pool:
        async with pool.acquire() as connection, connection.transaction():
            return await RijekaGeographyImporter(connection).apply(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Write the reviewed snapshot to DATABASE_URL.')
    args = parser.parse_args()
    data = json.loads(DATA_FILE.read_text())
    if args.apply:
        print(json.dumps(asyncio.run(import_geography(data)), ensure_ascii=False))
    else:
        for item in data['objects']:
            print(item['location_name'], item['review_status'], item.get('review_note', ''))


if __name__ == '__main__':
    main()
