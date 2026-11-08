"""LocalAddressLookup searches an offline OSM index without sharing home addresses."""
from pathlib import Path
from contextlib import closing
import re
import sqlite3
import unicodedata

from KIDSic.integrations.interfaces.address import AddressLookup


# City names and postcodes say nothing within one city's index.
CITY_WORDS = {'Rijeka': {'rijeka', '51000'}, 'Zagreb': {'zagreb', '10000'}, 'Šibenik': {'sibenik', '22000'}}
STREET_WORDS = {'ulica', 'ul'}
DUPLICATE_DEGREES = .0003  # about 30 m: the same address mapped twice


def normalized_address(text, city='Rijeka'):
    """normalized_address folds case and diacritics and drops words every
    address in the city shares, so "Ul. Zametska 6, Rijeka" matches "zametska 6"."""
    text = unicodedata.normalize('NFKD', text.casefold().replace('đ', 'd'))
    text = ''.join(c for c in text if not unicodedata.combining(c))
    ignored = STREET_WORDS | CITY_WORDS[city]
    return ' '.join(w for w in re.sub(r'[^a-z0-9]+', ' ', text).split() if w not in ignored)


class LocalAddressLookup(AddressLookup):
    def __init__(self, path: Path, city: str = 'Rijeka'):
        self._city = city
        self._path = path

    def find(self, query: str):
        if not self._path.is_file():
            raise OSError('Local OSM address index is missing.')
        key = normalized_address(query, self._city)
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
            if any(item['label'] == label and abs(lat - item['point']['lat']) < DUPLICATE_DEGREES
                   and abs(lon - item['point']['lon']) < DUPLICATE_DEGREES for item in result):
                continue
            result.append({'label': label, 'point': {'lat': lat, 'lon': lon},
                           'match': match, 'source': 'OpenStreetMap', 'license': 'ODbL-1.0'})
        return result[:6]
