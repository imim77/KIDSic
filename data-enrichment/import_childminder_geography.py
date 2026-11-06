"""Store reviewed seat geography without creating childminder service facilities."""
from pathlib import Path
import uuid

from reviewed_snapshot import OSM_COPYRIGHT, Batch, run

DATA_FILE = Path(__file__).with_name('varazdin-childminders-nominatim.json')
SOURCE_KEY = 'varazdin-childminders-osm'


async def import_geography(connection, data):
    batch = await Batch.start(connection, data['fetched_at'])
    source = await batch.source(SOURCE_KEY, 'OpenStreetMap — sjedišta varaždinskih dadilja',
                                'OpenStreetMap contributors', OSM_COPYRIGHT, data['licence'],
                                {'attribution': data['attribution'], 'cache_file': DATA_FILE.name})
    for item in data['objects']:
        owner = uuid.UUID(item['id'])
        stored = await connection.fetchrow(
            'SELECT name,seat_address,provider_kind FROM kindergarten WHERE id=$1 FOR UPDATE', owner)
        if (stored is None or stored['name'] != item['name'] or
                stored['seat_address'] != item['seat_address'] or stored['provider_kind'] != 'childminder'):
            raise ValueError(f"Review the changed childminder identity/address: {item['name']}")
        if item['review_status'] != 'matched':
            raise ValueError('Only reviewed address matches may be imported.')
        geo = item['selected']
        record = await batch.record(source, item['source_key'],
                                    {**item, 'evidence_scope': 'registered_seat_geography'},
                                    owner, note=item['review_note'])
        keys = ('quarter', 'suburb', 'neighbourhood', 'settlement')
        attributes = {key: geo.get(key) for key in keys}
        attributes.update(address=item['seat_address'], geocoding_address=item['geocoding_address'],
                          match_basis=geo['match_basis'], review_note=item['review_note'])
        await connection.execute('''
            UPDATE kindergarten SET seat_longitude=$2,seat_latitude=$3,seat_attributes=$4,
                provenance=provenance || jsonb_build_object('seat_geography',$5::jsonb)
            WHERE id=$1
        ''', owner, geo['longitude'], geo['latitude'], attributes,
            {'source_record_id': str(record), 'dataset_key': SOURCE_KEY})
        areas = ', '.join(f'{key}: {geo[key]}' for key in keys if geo.get(key))
        await batch.chunk(owner, None, record,
                          f"{item['name']}. Sjedište: {item['seat_address']}, {item['seat_settlement']}. "
                          f"Adresa geokodiranja: {item['geocoding_address']}. {areas}. "
                          f"Koordinate sjedišta: {geo['latitude']}, {geo['longitude']}. "
                          f"Mjesto rada nije neovisno potvrđeno. {data['attribution']}, {data['licence']}.",
                          geo['osm_url'])
    return {'imported': len(data['objects'])}


if __name__ == '__main__':
    run(__doc__, DATA_FILE, import_geography)
