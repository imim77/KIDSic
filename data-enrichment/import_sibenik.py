"""SibenikLocationImporter adds reviewed OSM facilities to active MZOM institutions."""
import argparse
import asyncio
from datetime import datetime
import json
from pathlib import Path
from uuid import uuid4

from KIDSic.config.routing import ROUTING_CITIES
from KIDSic.db.database import database_pool
from KIDSic.dto.source import name_key
from KIDSic.dto.text import normalize

DATA_FILE = Path(__file__).with_name('sibenik-reviewed-locations.geojson')
SOURCE_KEY = 'sibenik-reviewed-osm'


class SibenikLocationImporter:
    def __init__(self, connection):
        self._connection = connection

    @staticmethod
    def reviewed(data):
        if data.get('type') != 'FeatureCollection' or data.get('license') != 'ODbL-1.0':
            raise ValueError('Provide the reviewed ODbL OSM collection.')
        rows = [f for f in data['features'] if f['properties']['review_status'] == 'matched']
        if not rows:
            raise ValueError('No reviewed facilities; preserve the last good snapshot.')
        ids = set()
        for feature in rows:
            p, g = feature['properties'], feature['geometry']
            tags = p['osm_tags']
            lon, lat = g['coordinates']
            if (feature['id'] in ids or g['type'] != 'Point'
                    or not feature['id'].startswith(('node/', 'way/'))
                    or not all(type(v) in (int, float) for v in (lat, lon))
                    or not ROUTING_CITIES['Šibenik'].contains(lat, lon)
                    or tags.get('amenity') != 'kindergarten'
                    or normalize(tags.get('addr:city', '')) != 'sibenik'
                    or not tags.get('name') or not tags.get('addr:street')
                    or not tags.get('addr:housenumber') or not p.get('review_note')
                    or not p.get('parent_name') or not p.get('parent_settlement')):
                raise ValueError('Review each facility identity, address and parent before import.')
            ids.add(feature['id'])
        datetime.fromisoformat(data['retrieved_at'])
        return rows

    async def apply(self, data):
        rows = self.reviewed(data)
        db = self._connection
        await db.execute('SELECT pg_advisory_xact_lock(194733,1)')
        parents = await db.fetch('''
            SELECT k.id,k.name,k.seat_settlement_key FROM kindergarten k
            WHERE EXISTS (SELECT 1 FROM source_record r JOIN data_source s ON s.id=r.source_id
              WHERE r.kindergarten_id=k.id AND r.location_id IS NULL
                AND r.match_status='accepted' AND s.dataset_key='national'
                AND s.import_allowed AND s.active_batch_id=r.batch_id)
        ''')
        resolved = []
        for feature in rows:
            p = feature['properties']
            matches = [r for r in parents if name_key(r['name']) == name_key(p['parent_name'])
                       and r['seat_settlement_key'] == normalize(p['parent_settlement'])]
            if len(matches) != 1:
                raise ValueError(f"Import or review the national parent: {p['parent_name']}")
            resolved.append((feature, matches[0]['id']))
        source = await db.fetchrow('''
            INSERT INTO data_source(dataset_key,title,publisher,url,license,import_allowed,metadata)
            VALUES ($1,'OpenStreetMap — šibenski objekti vrtića','OpenStreetMap contributors',
                    'https://www.openstreetmap.org/copyright','ODbL-1.0',true,$2)
            ON CONFLICT(dataset_key) DO UPDATE SET metadata=data_source.metadata || EXCLUDED.metadata
            RETURNING id,import_allowed
        ''', SOURCE_KEY, {k: data[k] for k in ('attribution', 'osm_snapshot', 'snapshot_sha256')})
        if not source['import_allowed']:
            raise ValueError('Import is disabled for reviewed Šibenik facilities.')
        municipality = await db.fetchval('''
            INSERT INTO municipality(key,name,county,aliases)
            VALUES ('sibenik','Šibenik','Šibensko-kninska županija',ARRAY['sibenika','sibeniku'])
            ON CONFLICT(key) DO UPDATE SET name=EXCLUDED.name RETURNING id
        ''')
        batch, fetched = uuid4(), datetime.fromisoformat(data['retrieved_at'])
        for feature, owner in resolved:
            p, osm_id = feature['properties'], feature['id']
            tags, (lon, lat) = p['osm_tags'], feature['geometry']['coordinates']
            address = f"{tags['addr:street']} {tags['addr:housenumber']}"
            old = await db.fetchrow('''
                SELECT r.location_id,l.kindergarten_id,l.municipality_id FROM source_record r
                JOIN location l ON l.id=r.location_id
                WHERE r.source_id=$1 AND r.source_key=$2 AND r.match_status='accepted'
                ORDER BY r.fetched_at DESC,r.id LIMIT 1
            ''', source['id'], osm_id)
            if old and (old['kindergarten_id'] != owner or old['municipality_id'] != municipality):
                raise ValueError('Review the changed OSM parent before moving a facility.')
            location = old['location_id'] if old else await db.fetchval('''
                INSERT INTO location(kindergarten_id,name,settlement,settlement_key,address,municipality_id)
                VALUES ($1,$2,'Šibenik','sibenik',$3,$4) RETURNING id
            ''', owner, tags['name'], address, municipality)
            record = await db.fetchval('''
                INSERT INTO source_record(source_id,batch_id,source_key,raw_data,fetched_at,
                                          kindergarten_id,location_id,match_status,match_method,match_note)
                VALUES ($1,$2,$3,$4,$5,$6,$7,'accepted','manual',$8) RETURNING id
            ''', source['id'], batch, osm_id, {**feature, 'reviewed_address': address},
                fetched, owner, location, p['review_note'])
            evidence = {'dataset_key': SOURCE_KEY, 'source_record_id': str(record)}
            await db.execute('''
                UPDATE location SET name=$2,address=$3,longitude=$4,latitude=$5,
                    provenance=provenance || $6 WHERE id=$1
            ''', location, tags['name'], address, lon, lat,
                {key: evidence for key in ('location_name', 'address', 'longitude', 'latitude')})
        # Only a complete successful import replaces the previously visible batch.
        await db.execute('UPDATE data_source SET active_batch_id=$2,fetched_at=$3 WHERE id=$1',
                         source['id'], batch, fetched)
        return {'imported': len(rows), 'excluded': len(data['features']) - len(rows)}


async def import_locations(data):
    async with database_pool() as pool:
        async with pool.acquire() as connection, connection.transaction():
            return await SibenikLocationImporter(connection).apply(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    data = json.loads(DATA_FILE.read_text())
    if args.apply:
        print(json.dumps(asyncio.run(import_locations(data)), ensure_ascii=False))
    else:
        SibenikLocationImporter.reviewed(data)
        for feature in data['features']:
            print(feature['id'], feature['properties']['review_status'],
                  feature['properties']['review_note'])


if __name__ == '__main__':
    main()
