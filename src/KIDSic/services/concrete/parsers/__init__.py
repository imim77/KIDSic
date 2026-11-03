"""Built-in schema adapters; this registry is separate from normalization policy."""
from .national import NationalDirectoryParser
from .zagreb import ZagrebLocationParser
from .childminder import ChildminderDirectoryParser


def default_parsers():
    return {'national': NationalDirectoryParser(),
            'municipal': ZagrebLocationParser(municipal_only=True),
            'other': ZagrebLocationParser(),
            'varazdin-childminders': ChildminderDirectoryParser()}
