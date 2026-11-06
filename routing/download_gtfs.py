"""Download pins the approved public city GTFS; no account or key is required."""
import argparse
import hashlib

import httpx

from KIDSic.config.routing import ROUTING_CITIES


def download(city_name='Rijeka'):
    city = ROUTING_CITIES[city_name]
    directory = city.directory
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / city.gtfs_filename
    temporary = directory / 'download.part'
    try:
        with httpx.stream('GET', city.gtfs_url, timeout=60, follow_redirects=True) as response:
            response.raise_for_status()
            size = 0
            with temporary.open('wb') as output:
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > 64 * 1024 * 1024:
                        raise ValueError('GTFS exceeds the download size limit.')
                    output.write(chunk)
        with temporary.open('rb') as archive:
            digest = hashlib.file_digest(archive, 'sha256').hexdigest()
        if digest != city.gtfs_sha256:
            raise ValueError('The publisher changed the archive. Review the new version before updating the pinned SHA256.')
        temporary.replace(target)
        print(f'Downloaded and SHA256-verified: {target}')
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--city', choices=ROUTING_CITIES, default='Rijeka')
    download(parser.parse_args().city)
