"""Store reviewed seat geography without creating childminder service facilities."""
import argparse
import asyncio
from datetime import datetime
import hashlib
import json
from pathlib import Path
import uuid
from KIDSic.db.database import database_pool

DATA_FILE = Path(__file__).with_name('varazdin-childminders-nominatim.json')


async def import_geography(data):
    async with database_pool() as pool:
        async with pool.acquire() as connection, connection.transaction():
            await connection.execute('SELECT pg_advisory_xact_lock(194733, 1)')
            batch = uuid.uuid4()
            source = await connection.fetchval('''
                INSERT INTO data_source(dataset_key,title,publisher,url,license,import_allowed,
                                        active_batch_id,fetched_at,metadata)
                VALUES ('varazdin-childminders-osm','OpenStreetMap — sjedišta varaždinskih dadilja',
                        'OpenStreetMap contributors','https://www.openstreetmap.org/copyright',
                        $1,true,$2,$3,$4)
                ON CONFLICT(dataset_key) DO UPDATE SET active_batch_id=EXCLUDED.active_batch_id,
                    fetched_at=EXCLUDED.fetched_at,metadata=EXCLUDED.metadata RETURNING id
            ''', data['licence'], batch, datetime.fromisoformat(data['fetched_at']),
                {'attribution': data['attribution'], 'cache_file': DATA_FILE.name})
            for item in data['objects']:
                owner = uuid.UUID(item['id'])
                stored = await connection.fetchrow('SELECT name,seat_address,provider_kind FROM kindergarten WHERE id=$1 FOR UPDATE', owner)
                if (stored is None or stored['name'] != item['name'] or
                        stored['seat_address'] != item['seat_address'] or stored['provider_kind'] != 'childminder'):
                    raise ValueError(f"Review the changed childminder identity/address: {item['name']}")
                if item['review_status'] != 'matched':
                    raise ValueError('Only reviewed address matches may be imported.')
                geo = item['selected']
                item = {**item, 'evidence_scope': 'registered_seat_geography'}
                record = await connection.fetchval('''
                    INSERT INTO source_record(source_id,batch_id,source_key,raw_data,kindergarten_id,
                                              match_status,match_method,match_note)
                    VALUES ($1,$2,$3,$4,$5,'accepted','manual',$6) RETURNING id
                ''', source, batch, item['source_key'], item, owner, item['review_note'])
                attributes = {key: geo.get(key) for key in ('quarter','suburb','neighbourhood','settlement')}
                attributes.update(address=item['seat_address'], geocoding_address=item['geocoding_address'],
                                  match_basis=geo['match_basis'], review_note=item['review_note'])
                await connection.execute('''
                    UPDATE kindergarten SET seat_longitude=$2,seat_latitude=$3,seat_attributes=$4,
                        provenance=provenance || jsonb_build_object('seat_geography',$5::jsonb)
                    WHERE id=$1
                ''', owner, geo['longitude'], geo['latitude'], attributes,
                    {'source_record_id':str(record),'dataset_key':'varazdin-childminders-osm'})
                areas = ', '.join(f'{key}: {geo[key]}' for key in
                                  ('quarter','suburb','neighbourhood','settlement') if geo.get(key))
                content = (f"{item['name']}. Sjedište: {item['seat_address']}, {item['seat_settlement']}. "
                           f"Adresa geokodiranja: {item['geocoding_address']}. {areas}. "
                           f"Koordinate sjedišta: {geo['latitude']}, {geo['longitude']}. "
                           f"Mjesto rada nije neovisno potvrđeno. {data['attribution']}, {data['licence']}.")
                await connection.execute('''
                    INSERT INTO knowledge_chunk(kindergarten_id,source_record_id,ordinal,content,source_url,content_sha256)
                    VALUES ($1,$2,0,$3,$4,$5)
                ''', owner, record, content, geo['osm_url'], hashlib.sha256(content.encode()).hexdigest())
            return len(data['objects'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    data = json.loads(DATA_FILE.read_text())
    if args.apply:
        print(f'Enriched {asyncio.run(import_geography(data))} registered seats.')
    else:
        for item in data['objects']:
            print(item['name'],item['geocoding_address'],item['selected'])


if __name__ == '__main__':
    main()
