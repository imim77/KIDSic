"""CityExtract retains complete highway ways and their turn restrictions."""
import argparse
from pathlib import Path

import osmium

from KIDSic.config.routing import ROUTING_CITIES


class CityExtract(osmium.SimpleHandler):
    def __init__(self, writer, city):
        super().__init__()
        self.writer = writer
        self.city = city
        self.nodes = set()
        self.ways = set()

    def node(self, node):
        if self.city.contains(node.location.lat, node.location.lon):
            self.nodes.add(node.id)

    def way(self, way):
        if 'highway' in way.tags and any(node.ref in self.nodes for node in way.nodes):
            self.ways.add(way.id)
            self.writer.add_way(way)

    def relation(self, relation):
        if relation.tags.get('type') == 'restriction' and any(
                m.type == 'w' and m.ref in self.ways for m in relation.members):
            self.writer.add_relation(relation)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--city', choices=ROUTING_CITIES, default='Rijeka')
    parser.add_argument('source', type=Path)
    parser.add_argument('target', type=Path)
    args = parser.parse_args()

    with osmium.BackReferenceWriter(args.target, args.source, overwrite=True,
                                     remove_tags=False) as writer:
        extract = CityExtract(writer, ROUTING_CITIES[args.city])
        extract.apply_file(str(args.source))
        print(f'Retained {len(extract.ways)} highway ways in {args.city} and surroundings.')
