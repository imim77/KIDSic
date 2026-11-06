"""Import reviewed municipal facilities and cached OSM areas without new geocoding calls."""
from pathlib import Path
import uuid

from reviewed_snapshot import AREAS, OSM_COPYRIGHT, Batch, area_attributes, run

INSTITUTION_ID = uuid.UUID('1e0f52b9-0586-41e2-b08d-9be22a2c3688')
DATA_FILE = Path(__file__).with_name('varazdin-municipal-nominatim.json')


async def import_facilities(connection, data):
    """import_facilities preserves object identity and attaches evidence to each field."""
    if not await connection.fetchval('SELECT id FROM kindergarten WHERE id=$1', INSTITUTION_ID):
        raise ValueError('The reviewed institution is missing; do not guess its identity.')
    municipality = await connection.fetchval("SELECT id FROM municipality WHERE key='varazdin'")
    if municipality is None:
        raise ValueError('Register Grad Varaždin before importing its facilities.')
    batch = await Batch.start(connection, data['fetched_at'])
    metadata = {'attribution': data['attribution'], 'cache_file': DATA_FILE.name}
    official = await batch.source('varazdin-municipal-facilities', 'Dječji vrtić Varaždin — objekti',
                                  'Dječji vrtić Varaždin', data['address_source'], None, metadata)
    osm = await batch.source('varazdin-municipal-osm', 'OpenStreetMap — varaždinski gradski vrtići',
                             'OpenStreetMap contributors', OSM_COPYRIGHT, data['licence'], metadata)
    for item in data['objects']:
        location = uuid.uuid5(INSTITUTION_ID, item['object'])
        matched = item['review_status'] == 'matched' and item.get('selected') is not None
        geo = item['selected'] if matched else {}  # Candidates stay in raw evidence, not on the map.
        attributes, manual = area_attributes(
            geo, await connection.fetchval('SELECT attributes FROM location WHERE id=$1', location))
        attributes['geocoding_review_status'] = item['review_status']
        for key, value in (('phone', item.get('official_phone')),
                           ('geocoding_address', item.get('geocoding_address'))):
            if value:
                attributes[key] = value
        await batch.location(location, INSTITUTION_ID, f"Dječji vrtić Varaždin - {item['object']}",
                             item['official_address'], item['official_settlement'], municipality,
                             geo.get('longitude'), geo.get('latitude'), attributes)
        record = await batch.record(official, item['object'], {
            'object': item['object'], 'address': item['official_address'],
            'settlement': item['official_settlement'], 'phone': item.get('official_phone'),
            'source_url': data['address_source']}, INSTITUTION_ID, location, note=item.get('review_note'))
        await batch.evidence(location, record, ('location_name', 'address', 'settlement')
                             + (('phone',) if item.get('official_phone') else ()), manual)
        record = await batch.record(osm, item['object'], item, INSTITUTION_ID, location,
                                    'accepted' if matched else 'candidate', item.get('review_note'))
        if matched:
            await batch.evidence(location, record, ('longitude', 'latitude', *AREAS), manual)
            await batch.chunk(INSTITUTION_ID, location, record,
                              f"Dječji vrtić Varaždin, objekt {item['object']}. "
                              f"Adresa: {item['official_address']}, {item['official_settlement']}. "
                              f"Quarter: {geo.get('quarter')}; suburb: {geo.get('suburb')}. "
                              f"Koordinate: {geo['latitude']}, {geo['longitude']}. "
                              f"{data['attribution']}, {data['licence']}.", geo['osm_url'])
    return {'imported': len(data['objects'])}


if __name__ == '__main__':
    run(__doc__, DATA_FILE, import_facilities)
