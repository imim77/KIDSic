"""create_app links city-specific location reads to the embedded map resource."""
from contextlib import asynccontextmanager
import base64
import gzip
import logging
import os
from pathlib import Path

from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.routing import Route

from KIDSic.config.settings import Settings
from KIDSic.dto.location import LocationQuery, LocationMetadata
from KIDSic.services.dependency import DependencyService
from KIDSic.services.interfaces.location import LocationServiceInterface

logger = logging.getLogger(__name__)
UI_URI = 'ui://kidsic/map-v5.html'
UI_MIME = 'text/html;profile=mcp-app'
SERVER_INSTRUCTIONS = (
    'When the user asks to show or find kindergartens in a city, ALWAYS call '
    'prikazi_vrtice to display the interactive map and cards. '
    'A city explicitly supplied by the user is required. If the city is missing '
    'or ambiguous, ask the user which city before calling the tool. Never infer '
    'a city from location, history, or a default. Do not replace the map with '
    'a text-only list. Explain unavailable results without inventing data.'
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


def error_result(message: str) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type='text', text=message)], isError=True,
        _meta=TOOL_META,
    )


def create_app(service: LocationServiceInterface | None = None,
               ui_path: Path | str | None = None) -> Starlette:
    """create_app owns one location service and serves its self-contained UI build."""
    asset = Path(ui_path) if ui_path is not None else Path(os.environ.get('KIDSIC_UI_PATH', 'frontend/dist/mcp.html'))
    server = Server('KIDSic', version='0.1.0', instructions=SERVER_INSTRUCTIONS)
    state = {}

    @server.list_tools()
    async def list_tools():
        return [types.Tool(
            name='prikazi_vrtice', title='Prikaži vrtiće na karti',
            description=(
                'ALWAYS use this tool when the user asks to show or find '
                'kindergartens in a city. Displays the map and scrollable cards. '
                'REQUIRES a city supplied explicitly by the user. If no city '
                'is given, ask "U kojem gradu želiš prikaz vrtića?" first. '
                'Never assume Zagreb or any other city.'
            ),
            inputSchema={
                'type': 'object', 'properties': {'city': {
                    'type': 'string', 'minLength': 1, 'maxLength': 100,
                    'description': 'Naziv grada koji je korisnik izričito naveo.',
                }}, 'required': ['city'], 'additionalProperties': False,
            },
            outputSchema={
                'type': 'object', 'properties': {
                    'city': {'type': 'string'},
                    'metadata': LocationMetadata.model_json_schema(),
                }, 'required': ['city', 'metadata'], 'additionalProperties': False,
            },
            annotations=types.ToolAnnotations(
                readOnlyHint=True, destructiveHint=False, idempotentHint=True,
                openWorldHint=False,
            ),
            _meta=TOOL_META,
        )]

    # Validation here provides the same actionable missing-city response for all
    # clients, including those which do not enforce the advertised input schema.
    @server.call_tool(validate_input=False)
    async def call_tool(name, arguments):
        if name != 'prikazi_vrtice':
            return error_result('Nepoznat alat.')
        if not isinstance(arguments, dict) or set(arguments) != {'city'}:
            return error_result('Grad je obavezan. Pitaj korisnika: U kojem gradu želiš prikaz vrtića?')
        try:
            query = LocationQuery.model_validate({'city': arguments['city']})
        except ValidationError:
            return error_result('Navedi valjan naziv grada (1–100 znakova). Pitaj korisnika za grad.')
        try:
            locations = await state['locations'].list_locations(query)
        except Exception:
            logger.exception('MCP location read failed.')
            return error_result('Vrtići trenutačno nisu dostupni. Pokušaj ponovno kasnije.')
        return types.CallToolResult(
            content=[types.TextContent(type='text', text=(
                f'Prikaz vrtića za grad {query.city}: {locations.metadata.total} '
                f'rezultata, {locations.metadata.mapped} s koordinatama. '
                'Prikaži povezanu kartu i kartice.'
            ))],
            structuredContent={'city': query.city,
                               'metadata': locations.metadata.model_dump(mode='json')},
            # Host size limits also apply to UI-only metadata. Keep provenance
            # lossless while fitting large cities into the tool-result budget.
            _meta={**TOOL_META, 'locations': {
                'encoding': 'gzip+base64',
                'data': base64.b64encode(gzip.compress(
                    locations.model_dump_json().encode('utf-8'), mtime=0,
                )).decode('ascii'),
            }},
        )

    @server.list_resources()
    async def list_resources():
        return [types.Resource(uri=UI_URI, name='kidsic-map', title='Karta vrtića',
                               mimeType=UI_MIME, _meta=RESOURCE_META)]

    @server.read_resource()
    async def read_resource(uri):
        if str(uri) != UI_URI:
            raise ValueError('Nepoznat UI resurs.')
        return [ReadResourceContents(content=state['html'], mime_type=UI_MIME,
                                     meta=RESOURCE_META)]

    manager = StreamableHTTPSessionManager(server, stateless=True, json_response=True)

    @asynccontextmanager
    async def lifespan(app):
        try:
            state['html'] = asset.read_text(encoding='utf-8')
        except OSError as error:
            raise RuntimeError(
                f'MCP UI build missing or unreadable at {asset}. '
                'Run npm --prefix frontend run build:mcp first.'
            ) from error
        try:
            if service is not None:
                state['locations'] = service
                async with manager.run():
                    yield
            else:
                dependencies = DependencyService(Settings.from_env())
                async with dependencies.location_service() as locations:
                    state['locations'] = locations
                    async with manager.run():
                        yield
        finally:
            state.clear()

    class McpEndpoint:
        async def __call__(self, scope, receive, send):
            await manager.handle_request(scope, receive, send)

    return Starlette(routes=[Route('/mcp', McpEndpoint(),
                                  methods=['GET', 'POST', 'DELETE'])], lifespan=lifespan)
