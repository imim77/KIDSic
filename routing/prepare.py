"""Prepare pins the chosen GTFS bytes and records locally supplied OSM provenance."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from KIDSic.dto.day_route import GTFS_SHA256, GTFS_URL, SERVICE_START, SERVICE_END
REQUIRED = {'agency.txt', 'stops.txt', 'routes.txt', 'trips.txt', 'stop_times.txt'}


def prepare(gtfs: Path, osm: Path, osm_source: str):
    with gtfs.open('rb') as archive:
        digest = hashlib.file_digest(archive, 'sha256').hexdigest()
    if digest != GTFS_SHA256:
        raise ValueError('GTFS SHA256 does not match the approved Rijeka snapshot.')
    with zipfile.ZipFile(gtfs) as archive:
        names = set(archive.namelist())
        if not REQUIRED <= names or not {'calendar.txt', 'calendar_dates.txt'} & names:
            raise ValueError('GTFS is missing required tables.')
        if archive.testzip():
            raise ValueError('GTFS contains a corrupt file.')
    if osm.suffix != '.pbf' or not osm.is_file() or osm.stat().st_size == 0:
        raise ValueError('Provide a non-empty OpenStreetMap .osm.pbf extract.')
    target = Path(__file__).resolve().parent / 'data'
    target.mkdir(exist_ok=True)
    if gtfs.resolve() != (target / 'autotrolej-gtfs.zip').resolve():
        shutil.copyfile(gtfs, target / 'autotrolej-gtfs.zip')
    if osm.resolve() != (target / 'rijeka.osm.pbf').resolve():
        shutil.copyfile(osm, target / 'rijeka.osm.pbf')
    shutil.copyfile(Path(__file__).with_name('build-config.json'), target / 'build-config.json')
    with osm.open('rb') as extract:
        osm_digest = hashlib.file_digest(extract, 'sha256').hexdigest()
    manifest = {'gtfs_sha256': GTFS_SHA256, 'gtfs_url': GTFS_URL,
                'service_start': str(SERVICE_START), 'service_end': str(SERVICE_END), 'osm_source': osm_source,
                'osm_sha256': osm_digest,
                'osm_license': 'ODbL-1.0', 'gtfs_license': 'CC-BY-4.0 (Transitous source registry)',
                'gtfs_license_verification': 'https://transitous.org/sources/#croatia'}
    (target / 'provenance.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Validated and prepared input data in {target}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gtfs', type=Path, required=True)
    parser.add_argument('--osm', type=Path, required=True)
    parser.add_argument('--osm-source', required=True)
    args = parser.parse_args()
    prepare(args.gtfs, args.osm, args.osm_source)
