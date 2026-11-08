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
            'SELECT k.naziv AS name,ks.adresa AS seat_address,k.vrsta_pruzatelja  AS provider_kind FROM vrtici k LEFT JOIN sjedista_vrtica ks ON ks.id_vrtica=k.id WHERE k.id=$1 FOR UPDATE OF k', owner)
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
        await connection.execute("""
            UPDATE sjedista_vrtica SET geografska_duzina=$2,geografska_sirina=$3,obiljezja=$4,
                id_zapisa_geografskog_izvora=$5 WHERE id_vrtica=$1
        """, owner, geo['longitude'], geo['latitude'], attributes, record)
        areas = ', '.join(f'{key}: {geo[key]}' for key in keys if geo.get(key))
        await batch.chunk(owner, None, record,
                          f"{item['name']}. Sjedište: {item['seat_address']}, {item['seat_settlement']}. "
                          f"Adresa geokodiranja: {item['geocoding_address']}. {areas}. "
                          f"Koordinate sjedišta: {geo['latitude']}, {geo['longitude']}. "
                          f"Mjesto rada nije neovisno potvrđeno. {data['attribution']}, {data['licence']}.",
                          geo['osm_url'])
    await batch.finish()
    return {'imported': len(data['objects'])}


if __name__ == '__main__':
    run(__doc__, DATA_FILE, import_geography)
