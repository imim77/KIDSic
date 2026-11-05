"""LocalAddressLookup searches an offline OSM index without sharing home addresses."""
from pathlib import Path
from contextlib import closing
import re
import sqlite3
import unicodedata

from KIDSic.integrations.interfaces.address import AddressLookup


def normalized_address(text):
    text = unicodedata.normalize('NFKD', text.casefold().replace('đ', 'd'))
    text = ''.join(c for c in text if not unicodedata.combining(c))
    words = re.sub(r'[^a-z0-9]+', ' ', text).split()
    return ' '.join(w for w in words if w not in {'rijeka', 'ulica', 'ul', '51000'})


class LocalAddressLookup(AddressLookup):
    def __init__(self, path: Path):
        self._path = path

    def find(self, query: str):
        if not self._path.is_file():
            raise OSError('Local OSM address index is missing.')
        key = normalized_address(query)
        if not key:
            return []
        with closing(sqlite3.connect(self._path.as_uri() + '?mode=ro', uri=True)) as db:
            exact = db.execute('SELECT label,lat,lon FROM addresses WHERE normalized=? ORDER BY id',
                               (key,)).fetchall()
            if exact:
                rows, match = exact, 'exact'
            else:
                terms = key.split()
                rows = db.execute('SELECT label,lat,lon FROM addresses WHERE ' +
                    ' AND '.join('normalized LIKE ?' for _ in terms) + ' ORDER BY label LIMIT 6',
                    [f'%{word}%' for word in terms]).fetchall()
                match = 'partial'
        result = []
        for label, lat, lon in rows:
            if any(item['label'] == label and abs(lat-item['point']['lat']) < .0003
                   and abs(lon-item['point']['lon']) < .0003 for item in result):
                continue
            result.append({'label': label, 'point': {'lat': lat, 'lon': lon},
                           'match': match, 'source': 'OpenStreetMap', 'license': 'ODbL-1.0'})
        return result[:6]
