"""Import reviewed municipal facilities and cached OSM areas without new geocoding calls."""
import argparse
import asyncio
from datetime import datetime
import hashlib
import json
from pathlib import Path
import uuid

from KIDSic.db.database import database_pool
from KIDSic.dto.text import normalize

INSTITUTION_ID = uuid.UUID('1e0f52b9-0586-41e2-b08d-9be22a2c3688')
DATA_FILE = Path(__file__).with_name('varazdin-municipal-nominatim.json')


async def import_facilities(data):
    """Import_facilities preserves object identity and attaches evidence to each field."""
    async with database_pool() as pool:
        async with pool.acquire() as connection, connection.transaction():
            if not await connection.fetchval('SELECT id FROM kindergarten WHERE id=$1', INSTITUTION_ID):
                raise ValueError('The reviewed institution is missing; do not guess its identity.')
            municipality = await connection.fetchval("SELECT id FROM municipality WHERE key='varazdin'")
            if municipality is None:
                raise ValueError('Register Grad Varaždin before importing its facilities.')
            batch = uuid.uuid4()
            sources = {}
            for key, title, publisher, url, license in (
                ('varazdin-municipal-facilities', 'Dječji vrtić Varaždin — objekti',
                 'Dječji vrtić Varaždin', data['address_source'], None),
                ('varazdin-municipal-osm', 'OpenStreetMap — varaždinski gradski vrtići',
                 'OpenStreetMap contributors', 'https://www.openstreetmap.org/copyright', data['licence']),
            ):
                sources[key] = await connection.fetchval('''
                    INSERT INTO data_source(dataset_key,title,publisher,url,license,import_allowed,
                                            active_batch_id,fetched_at,metadata)
                    VALUES ($1,$2,$3,$4,$5,true,$6,$7::timestamptz,$8)
                    ON CONFLICT(dataset_key) DO UPDATE SET active_batch_id=EXCLUDED.active_batch_id,
                        fetched_at=EXCLUDED.fetched_at,metadata=EXCLUDED.metadata
                    RETURNING id
                ''', key, title, publisher, url, license, batch,
                    datetime.fromisoformat(data['fetched_at']),
                    {'attribution': data['attribution'], 'cache_file': DATA_FILE.name})
            for item in data['objects']:
                location_id = uuid.uuid5(INSTITUTION_ID, item['object'])
                selected = item.get('selected')
                matched = item['review_status'] == 'matched' and selected is not None
                # Address candidates remain in raw evidence; they do not become map pins.
                geo = selected if matched else {}
                attributes = {key: geo.get(key) for key in ('quarter', 'suburb', 'neighbourhood')}
                attributes['geocoding_review_status'] = item['review_status']
                if item.get('official_phone'):
                    attributes['phone'] = item['official_phone']
                if item.get('geocoding_address'):
                    attributes['geocoding_address'] = item['geocoding_address']
                # Explicit user corrections survive another geocoding snapshot.
                existing = await connection.fetchval('SELECT attributes FROM location WHERE id=$1', location_id)
                manual_area = (existing or {}).get('manual_area', {})
                attributes.update({key: manual_area[key] for key in ('quarter', 'suburb') if key in manual_area})
                await connection.execute('''
                    INSERT INTO location(id,kindergarten_id,name,address,settlement,settlement_key,
                                         municipality_id,longitude,latitude,attributes)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                    ON CONFLICT(id) DO UPDATE SET name=EXCLUDED.name,address=EXCLUDED.address,
                        settlement=EXCLUDED.settlement,settlement_key=EXCLUDED.settlement_key,
                        municipality_id=EXCLUDED.municipality_id,longitude=EXCLUDED.longitude,
                        latitude=EXCLUDED.latitude,attributes=location.attributes || EXCLUDED.attributes
                ''', location_id, INSTITUTION_ID, f"Dječji vrtić Varaždin - {item['object']}", item['official_address'],
                    item['official_settlement'], normalize(item['official_settlement']), municipality,
                    geo.get('longitude'), geo.get('latitude'), attributes)
                provenance = {}
                for key, raw, status in (
                    ('varazdin-municipal-facilities', {
                        'object': item['object'], 'address': item['official_address'],
                        'settlement': item['official_settlement'], 'phone': item.get('official_phone'),
                        'source_url': data['address_source'],
                    }, 'accepted'),
                    ('varazdin-municipal-osm', item, 'accepted' if matched else 'candidate'),
                ):
                    record = await connection.fetchval('''
                        INSERT INTO source_record(source_id,batch_id,source_key,raw_data,fetched_at,
                                                  kindergarten_id,location_id,match_status,match_method,match_note)
                        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'manual',$9) RETURNING id
                    ''', sources[key], batch, item['object'], raw,
                        datetime.fromisoformat(data['fetched_at']),
                        INSTITUTION_ID, location_id, status, item.get('review_note'))
                    fields = ('location_name', 'address', 'settlement') if key.endswith('facilities') else (
                        ('longitude', 'latitude', 'quarter', 'suburb', 'neighbourhood') if matched else ())
                    if key.endswith('facilities') and item.get('official_phone'):
                        fields += ('phone',)
                    for field in fields:
                        if field in manual_area:
                            continue
                        provenance[field] = {'source_record_id': str(record)}
                    if key.endswith('osm') and matched:
                        content = (f"Dječji vrtić Varaždin, objekt {item['object']}. "
                                   f"Adresa: {item['official_address']}, {item['official_settlement']}. "
                                   f"Quarter: {geo.get('quarter')}; suburb: {geo.get('suburb')}. "
                                   f"Koordinate: {geo['latitude']}, {geo['longitude']}. "
                                   f"{data['attribution']}, {data['licence']}.")
                        await connection.execute('''
                            INSERT INTO knowledge_chunk(kindergarten_id,location_id,source_record_id,
                                                        ordinal,content,source_url,content_sha256)
                            VALUES ($1,$2,$3,0,$4,$5,$6)
                        ''', INSTITUTION_ID, location_id, record, content, geo['osm_url'],
                            hashlib.sha256(content.encode()).hexdigest())
                await connection.execute('UPDATE location SET provenance=provenance || $2 WHERE id=$1',
                                         location_id, provenance)
            return len(data['objects'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Write the reviewed snapshot to DATABASE_URL.')
    args = parser.parse_args()
    data = json.loads(DATA_FILE.read_text())
    if args.apply:
        print(f'Imported {asyncio.run(import_facilities(data))} facilities.')
    else:
        for item in data['objects']:
            geo = item.get('selected') or {}
            print(item['object'], item['review_status'], geo.get('quarter'), geo.get('suburb'))


if __name__ == '__main__':
    main()
