"""RijekaExtract retains complete highway ways and their turn restrictions."""
import argparse
from pathlib import Path

import osmium


class RijekaExtract(osmium.SimpleHandler):
    def __init__(self, writer):
        super().__init__()
        self.writer = writer
        self.nodes = set()
        self.ways = set()

    def node(self, node):
        if 14.20 <= node.location.lon <= 14.65 and 45.20 <= node.location.lat <= 45.45:
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
    parser.add_argument('source', type=Path)
    parser.add_argument('target', type=Path)
    args = parser.parse_args()
    # Back references retain nodes beyond the box when a road crosses its edge.
    with osmium.BackReferenceWriter(args.target, args.source, overwrite=True,
                                     remove_tags=False) as writer:
        extract = RijekaExtract(writer)
        extract.apply_file(str(args.source))
        print(f'Retained {len(extract.ways)} highway ways in Rijeka and surroundings.')
