"""Import reviewed Varaždin venues, keeping institution seats and field evidence separate."""
import argparse
import asyncio
from datetime import datetime
import hashlib
import json
from pathlib import Path
import uuid

from KIDSic.db.database import database_pool
from KIDSic.dto.text import normalize

DATA_FILE = Path(__file__).with_name('varazdin-other-nominatim.json')


async def import_venues(data):
    """Import_venues links each reviewed physical venue to its existing institution."""
    async with database_pool() as pool:
        async with pool.acquire() as connection, connection.transaction():
            municipality = await connection.fetchval("SELECT id FROM municipality WHERE key='varazdin'")
            if municipality is None:
                raise ValueError('Register Grad Varaždin before importing venues.')
            batch = uuid.uuid4()
            fetched_at = datetime.fromisoformat(data['fetched_at'])
            sources = {}
            for item in data['objects']:
                institution_id = uuid.UUID(item['kindergarten_id'])
                name = await connection.fetchval('SELECT name FROM kindergarten WHERE id=$1', institution_id)
                if name != item['name'] or item['review_status'] != 'matched':
                    raise ValueError(f"Review the identity and geocoding of {item['name']} before import.")
                geo = item['selected']
                location_id = uuid.uuid5(institution_id, item['location_key'])
                existing = await connection.fetchval('SELECT attributes FROM location WHERE id=$1', location_id)
                manual_area = (existing or {}).get('manual_area', {})
                attributes = {key: geo.get(key) for key in ('quarter', 'suburb', 'neighbourhood')}
                attributes.update({key: manual_area[key] for key in ('quarter', 'suburb') if key in manual_area})
                attributes.update(venue_role=item['venue_role'], geocoding_review_status='matched',
                                  geocoding_match_basis=geo['match_basis'])
                await connection.execute('''
                    INSERT INTO location(id,kindergarten_id,name,address,settlement,settlement_key,
                                         municipality_id,longitude,latitude,attributes)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                    ON CONFLICT(id) DO UPDATE SET name=EXCLUDED.name,address=EXCLUDED.address,
                        settlement=EXCLUDED.settlement,settlement_key=EXCLUDED.settlement_key,
                        municipality_id=EXCLUDED.municipality_id,longitude=EXCLUDED.longitude,
                        latitude=EXCLUDED.latitude,attributes=location.attributes || EXCLUDED.attributes
                ''', location_id, institution_id, item['object'], item['official_address'],
                    item['official_settlement'], normalize(item['official_settlement']), municipality,
                    geo['longitude'], geo['latitude'], attributes)
                provenance = {}
                for role, title, publisher, url, license, fields in (
                    ('venue', 'Varaždin — objavljene lokacije ustanova i programa',
                     'Grad Varaždin / pružatelj programa', item['address_source'], None,
                     ('location_name', 'address', 'settlement')),
                    ('osm', 'OpenStreetMap — ostale varaždinske ustanove',
                     'OpenStreetMap contributors', 'https://www.openstreetmap.org/copyright',
                     data['licence'], ('longitude', 'latitude', 'quarter', 'suburb', 'neighbourhood')),
                ):
                    source_key = f"varazdin-other-{role}-" + hashlib.sha256(url.encode()).hexdigest()[:16]
                    if source_key not in sources:
                        sources[source_key] = await connection.fetchval('''
                            INSERT INTO data_source(dataset_key,title,publisher,url,license,
                                                    import_allowed,active_batch_id,fetched_at,metadata)
                            VALUES ($1,$2,$3,$4,$5,true,$6,$7,$8)
                            ON CONFLICT(dataset_key) DO UPDATE SET active_batch_id=EXCLUDED.active_batch_id,
                                fetched_at=EXCLUDED.fetched_at,metadata=EXCLUDED.metadata
                            RETURNING id
                        ''', source_key, title, publisher, url, license, batch, fetched_at,
                            {'cache_file': DATA_FILE.name, 'attribution': data['attribution'] if role == 'osm' else None})
                    record = await connection.fetchval('''
                        INSERT INTO source_record(source_id,batch_id,source_key,raw_data,fetched_at,
                                                  kindergarten_id,location_id,match_status,match_method,match_note)
                        VALUES ($1,$2,$3,$4,$5,$6,$7,'accepted','manual',$8) RETURNING id
                    ''', sources[source_key], batch, item['location_key'], item, fetched_at,
                        institution_id, location_id, item['review_note'])
                    for field in fields:
                        if field not in manual_area:
                            provenance[field] = {'source_record_id': str(record)}
                    if role == 'osm':
                        areas = ', '.join(f'{key}: {attributes[key]}' for key in
                                          ('quarter', 'suburb', 'neighbourhood') if attributes.get(key))
                        content = (f"{name}; lokacija: {item['object']}. "
                                   f"Adresa: {item['official_address']}, {item['official_settlement']}. "
                                   f"{areas}. Koordinate: {geo['latitude']}, {geo['longitude']}. "
                                   f"Vrsta lokacije: {item['venue_role']}. "
                                   f"Izvor lokacije: {item['address_source']}. "
                                   f"{data['attribution']}, {data['licence']}.")
                        await connection.execute('''
                            INSERT INTO knowledge_chunk(kindergarten_id,location_id,source_record_id,
                                                        ordinal,content,source_url,content_sha256)
                            VALUES ($1,$2,$3,0,$4,$5,$6)
                        ''', institution_id, location_id, record, content, geo['osm_url'],
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
        print(f'Imported {asyncio.run(import_venues(data))} venues.')
    else:
        for item in data['objects']:
            print(item['object'], item['official_address'], item['selected'])


if __name__ == '__main__':
    main()
