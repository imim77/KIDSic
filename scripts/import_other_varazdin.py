"""Import reviewed Varaždin venues, keeping institution seats and field evidence separate."""
import hashlib
from pathlib import Path
import uuid

from reviewed_snapshot import AREAS, OSM_COPYRIGHT, Batch, area_attributes, run

DATA_FILE = Path(__file__).with_name('varazdin-other-nominatim.json')


async def import_venues(connection, data):
    """import_venues links each reviewed physical venue to its existing institution."""
    municipality = await connection.fetchval("SELECT id FROM jedinice_lokalne_samouprave WHERE key='varazdin'")
    if municipality is None:
        raise ValueError('Register Grad Varaždin before importing venues.')
    batch = await Batch.start(connection, data['fetched_at'])
    sources = {}

    async def source(role, title, publisher, url, license):
        # One data source per published URL, shared by every venue it lists.
        key = f'varazdin-other-{role}-' + hashlib.sha256(url.encode()).hexdigest()[:16]
        if key not in sources:
            sources[key] = await batch.source(key, title, publisher, url, license, {
                'cache_file': DATA_FILE.name, 'attribution': data['attribution'] if role == 'osm' else None})
        return sources[key]

    for item in data['objects']:
        owner = uuid.UUID(item['kindergarten_id'])
        name = await connection.fetchval('SELECT name FROM vrtici WHERE id=$1', owner)
        if name != item['name'] or item['review_status'] != 'matched':
            raise ValueError(f"Review the identity and geocoding of {item['name']} before import.")
        geo = item['selected']
        location = uuid.uuid5(owner, item['location_key'])
        attributes, manual = area_attributes(
            geo, await connection.fetchval('SELECT attributes FROM objekti WHERE id=$1', location))
        attributes.update(venue_role=item['venue_role'], geocoding_review_status='matched',
                          geocoding_match_basis=geo['match_basis'])
        await batch.location(location, owner, item['object'], item['official_address'],
                             item['official_settlement'], municipality, geo['longitude'], geo['latitude'],
                             attributes)
        venue = await source('venue', 'Varaždin — objavljene lokacije ustanova i programa',
                             'Grad Varaždin / pružatelj programa', item['address_source'], None)
        record = await batch.record(venue, f"{owner}:{item['location_key']}", item, owner, location, note=item['review_note'])
        await batch.evidence(location, record, ('location_name', 'address', 'settlement'), manual)
        osm = await source('osm', 'OpenStreetMap — ostale varaždinske ustanove',
                           'OpenStreetMap contributors', OSM_COPYRIGHT, data['licence'])
        record = await batch.record(osm, f"{owner}:{item['location_key']}", item, owner, location, note=item['review_note'])
        await batch.evidence(location, record, ('longitude', 'latitude', *AREAS), manual)
        areas = ', '.join(f'{key}: {attributes[key]}' for key in AREAS if attributes.get(key))
        await batch.chunk(owner, location, record,
                          f"{name}; lokacija: {item['object']}. "
                          f"Adresa: {item['official_address']}, {item['official_settlement']}. "
                          f"{areas}. Koordinate: {geo['latitude']}, {geo['longitude']}. "
                          f"Vrsta lokacije: {item['venue_role']}. "
                          f"Izvor lokacije: {item['address_source']}. "
                          f"{data['attribution']}, {data['licence']}.", geo['osm_url'])
    await batch.finish()
    return {'imported': len(data['objects'])}


if __name__ == '__main__':
    run(__doc__, DATA_FILE, import_venues)
