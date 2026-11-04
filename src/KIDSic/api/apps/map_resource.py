"""MapResource owns the embedded HTML asset and its MCP resource contract."""
from pathlib import Path
from mcp import types
from mcp.server.lowlevel.helper_types import ReadResourceContents

UI_URI = 'ui://kidsic/map-v7.html'
UI_MIME = 'text/html;profile=mcp-app'
SERVER_INSTRUCTIONS = (
    'When the user asks to show or find kindergartens in a city, ALWAYS call '
    'prikazi_vrtice to display the interactive map and cards. '
    'A city explicitly supplied by the user is required. If the city is missing '
    'or ambiguous, ask the user which city before calling the tool. Never infer '
    'a city from location, history, or a default. Do not replace the map with '
    'a text-only list. Only Zagreb, Varaždin and Rijeka are supported; explain '
    'this limitation for other cities. Explain unavailable results without inventing data.'
)
TOOL_META = {
    'ui': {'resourceUri': UI_URI},
    'openai/outputTemplate': UI_URI,
    'openai/toolInvocation/invoking': 'Tražim vrtiće…',
    'openai/toolInvocation/invoked': 'Karta vrtića je spremna.',
}
MAPBOX_DOMAINS = ['https://api.mapbox.com', 'https://events.mapbox.com',
                  'https://*.tiles.mapbox.com']
RESOURCE_META = {
    'openai/ui': {'availableDisplayModes': ['inline', 'fullscreen']},
    'ui': {
        'prefersBorder': True,
        'csp': {'connectDomains': MAPBOX_DOMAINS,
                'resourceDomains': [*MAPBOX_DOMAINS, 'blob:', 'data:']},
    },
    'openai/widgetDescription': 'Karta vrtića s pomičnim karticama naziva i adresa.',
    'openai/widgetPrefersBorder': True,
    'openai/widgetCSP': {'connect_domains': MAPBOX_DOMAINS,
                         'resource_domains': [*MAPBOX_DOMAINS, 'blob:', 'data:']},
}


class MapResource:
    def __init__(self, path: Path):
        self._path = path
        self._html = None

    def load(self):
        try:
            self._html = self._path.read_text(encoding='utf-8')
        except OSError as error:
            raise RuntimeError(
                f'MCP UI build missing or unreadable at {self._path}. '
                'Run npm --prefix frontend run build:mcp first.'
            ) from error

    def close(self):
        self._html = None

    def register(self, server):
        server.list_resources()(self.list_resources)
        server.read_resource()(self.read_resource)

    async def list_resources(self):
        return [types.Resource(uri=UI_URI, name='kidsic-map', title='Karta vrtića',
                               mimeType=UI_MIME, _meta=RESOURCE_META)]

    async def read_resource(self, uri):
        if str(uri) != UI_URI:
            raise ValueError('Nepoznat UI resurs.')
        if self._html is None:
            raise RuntimeError('Map resource is not loaded.')
        return [ReadResourceContents(content=self._html, mime_type=UI_MIME,
                                     meta=RESOURCE_META)]
