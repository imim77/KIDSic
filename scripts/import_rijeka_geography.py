"""Import reviewed Rijeka geography into existing CSV facilities without HTTP calls."""
import math
from pathlib import Path
import uuid

from reviewed_snapshot import AREAS, OSM_COPYRIGHT, Batch, area_attributes, run

DATA_FILE = Path(__file__).with_name('rijeka-reviewed-geography.json')


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
        batch = await Batch.start(self._connection, data['fetched_at'])
        source = await batch.source('rijeka-reviewed-geography', 'OpenStreetMap — riječke lokacije vrtića',
                                    'OpenStreetMap contributors', OSM_COPYRIGHT, data['licence'],
                                    {'attribution': data['attribution'], 'cache_file': DATA_FILE.name})
        for item in accepted:
            location = uuid.UUID(item['location_id'])
            stored = await self._connection.fetchrow('''
                SELECT l.kindergarten_id,l.name,l.address,l.attributes
                FROM objekti l JOIN jedinice_lokalne_samouprave m ON m.id=l.municipality_id
                WHERE l.id=$1 AND m.key='rijeka' AND EXISTS (
                    SELECT 1 FROM izvorni_zapisi r JOIN izvori_podataka s ON s.id=r.source_id
                    WHERE r.location_id=l.id AND r.kindergarten_id=l.kindergarten_id
                      AND s.dataset_key='rijeka-kindergartens' AND r.source_key=$2
                      AND s.import_allowed
                      AND r.match_status='accepted') FOR UPDATE OF l
            ''', location, item['source_key'])
            if (stored is None or str(stored['kindergarten_id']) != item['kindergarten_id']
                    or stored['name'] != item['location_name'] or stored['address'] != item['address']):
                raise ValueError(f"Review the changed Rijeka location: {item['location_name']}")
            geo = item['selected']
            record = await batch.record(source, item['source_key'], {**item, 'reviewed_address': item['address']},
                                        stored['kindergarten_id'], location, note=item['review_note'])
            attributes, manual = area_attributes(geo, stored['attributes'])
            attributes.update(geocoding_review_status='matched', geocoding_match_basis=geo['match_basis'])
            await self._connection.execute(
                'UPDATE objekti SET longitude=$2,latitude=$3,attributes=attributes || $4 WHERE id=$1',
                location, geo['longitude'], geo['latitude'], attributes)
            await batch.evidence(location, record, [field for field in ('longitude', 'latitude', *AREAS)
                                                    if geo.get(field) is not None], manual)
            areas = '; '.join(f'{key}: {attributes[key]}' for key in AREAS if attributes.get(key))
            await batch.chunk(stored['kindergarten_id'], location, record,
                              f"{item['location_name']}. Adresa: {item['address']}, Rijeka. "
                              f"{areas}. Koordinate: {geo['latitude']}, {geo['longitude']}. "
                              f"Podloga podudaranja: {geo['match_basis']}. "
                              f"OSM područja nisu potvrda službenih gradskih granica. "
                              f"{data['attribution']}; {data['licence']}.", geo['source_url'])
        await batch.finish()
        return {'imported': len(accepted), 'needs_review': len(data['objects']) - len(accepted)}


if __name__ == '__main__':
    run(__doc__, DATA_FILE, lambda connection, data: RijekaGeographyImporter(connection).apply(data))
