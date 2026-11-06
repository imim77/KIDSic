"""Prepare pins the chosen GTFS bytes and records locally supplied OSM provenance."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from KIDSic.config.routing import ROUTING_CITIES
REQUIRED = {'agency.txt', 'stops.txt', 'routes.txt', 'trips.txt', 'stop_times.txt'}


def prepare(gtfs: Path, osm: Path, osm_source: str, city_name: str = 'Rijeka'):
    city = ROUTING_CITIES[city_name]
    with gtfs.open('rb') as archive:
        digest = hashlib.file_digest(archive, 'sha256').hexdigest()
    if digest != city.gtfs_sha256:
        raise ValueError('GTFS SHA256 does not match the approved city snapshot.')
    with zipfile.ZipFile(gtfs) as archive:
        names = set(archive.namelist())
        if not REQUIRED <= names or not {'calendar.txt', 'calendar_dates.txt'} & names:
            raise ValueError('GTFS is missing required tables.')
        if archive.testzip():
            raise ValueError('GTFS contains a corrupt file.')
    if osm.suffix != '.pbf' or not osm.is_file() or osm.stat().st_size == 0:
        raise ValueError('Provide a non-empty OpenStreetMap .osm.pbf extract.')
    target = city.directory
    target.mkdir(parents=True, exist_ok=True)
    if gtfs.resolve() != (target / city.gtfs_filename).resolve():
        shutil.copyfile(gtfs, target / city.gtfs_filename)
    if osm.resolve() != (target / f'{city.key}.osm.pbf').resolve():
        shutil.copyfile(osm, target / f'{city.key}.osm.pbf')
    (target / 'build-config.json').write_text(json.dumps({
        'transitServiceStart': str(city.service_start),
        'transitServiceEnd': str(city.service_end)}, indent=2) + '\n')
    with osm.open('rb') as extract:
        osm_digest = hashlib.file_digest(extract, 'sha256').hexdigest()
    manifest = {'gtfs_sha256': city.gtfs_sha256, 'gtfs_url': city.gtfs_url,
                'service_start': str(city.service_start), 'service_end': str(city.service_end), 'osm_source': osm_source,
                'osm_sha256': osm_digest,
                'osm_license': 'ODbL-1.0', 'gtfs_license': city.license, 'gtfs_publisher': city.publisher, 'city': city.name,
                'gtfs_license_verification': city.license_url, 'retrieved_on': str(city.retrieved_on)}
    (target / 'provenance.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Validated and prepared input data in {target}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--city', choices=ROUTING_CITIES, default='Rijeka')
    parser.add_argument('--gtfs', type=Path, required=True)
    parser.add_argument('--osm', type=Path, required=True)
    parser.add_argument('--osm-source', required=True)
    args = parser.parse_args()
    prepare(args.gtfs, args.osm, args.osm_source, args.city)
