"""Download pins the approved public Rijeka GTFS; no account or key is required."""
import hashlib
from pathlib import Path

import httpx

from KIDSic.dto.day_route import GTFS_SHA256, GTFS_URL


def download():
    directory = Path(__file__).with_name('data')
    directory.mkdir(exist_ok=True)
    target = directory / 'autotrolej-gtfs.zip'
    temporary = directory / 'download.part'
    try:
        with httpx.stream('GET', GTFS_URL, timeout=60, follow_redirects=True) as response:
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
        if digest != GTFS_SHA256:
            raise ValueError('The publisher changed the archive. Review the new version before updating the pinned SHA256.')
        temporary.replace(target)
        print(f'Downloaded and SHA256-verified: {target}')
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    download()
