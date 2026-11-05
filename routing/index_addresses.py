"""AddressIndexBuilder extracts offline address and named POI coordinates from OSM."""
import argparse
from contextlib import closing
from pathlib import Path
import sqlite3

import osmium

from KIDSic.integrations.concrete.address import normalized_address


class AddressIndexBuilder(osmium.SimpleHandler):
    def __init__(self, db):
        super().__init__()
        self._db = db
        self.count = 0

    def _add(self, kind, identifier, tags, lat, lon):
        if not 45.20 <= lat <= 45.45 or not 14.20 <= lon <= 14.65:
            return
        city = tags.get('addr:city', '')
        if city and city.casefold() != 'rijeka':
            return
        street, number = tags.get('addr:street'), tags.get('addr:housenumber')
        if street and number:
            label = f'{street} {number}'
        elif tags.get('name') and any(k in tags for k in ('amenity', 'office', 'shop', 'tourism', 'leisure')):
            label = tags['name']
        else:
            return
        self._db.execute('INSERT INTO addresses VALUES (?,?,?,?,?)',
            (f'{kind}/{identifier}', label, normalized_address(label), lat, lon))
        self.count += 1

    def node(self, node):
        self._add('node', node.id, node.tags, node.location.lat, node.location.lon)

    def way(self, way):
        if not ('addr:housenumber' in way.tags or 'name' in way.tags):
            return
        nodes = [n.location for n in way.nodes if n.location.valid()]
        if nodes:
            self._add('way', way.id, way.tags,
                      sum(n.lat for n in nodes)/len(nodes), sum(n.lon for n in nodes)/len(nodes))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('target', type=Path)
    args = parser.parse_args()
    temporary = args.target.with_suffix('.part.sqlite')
    temporary.unlink(missing_ok=True)
    with closing(sqlite3.connect(temporary)) as db, db:
        db.execute('CREATE TABLE addresses (id TEXT PRIMARY KEY,label TEXT,normalized TEXT,lat REAL,lon REAL)')
        builder = AddressIndexBuilder(db)
        builder.apply_file(str(args.source), locations=True)
        db.execute('CREATE INDEX address_normalized ON addresses(normalized)')
        print(f'Indexed {builder.count} local OSM addresses and named places.')
    temporary.replace(args.target)
