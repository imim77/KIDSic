"""LocationTools translates MCP calls into location-service requests."""
import base64
import gzip
import logging
from collections.abc import Callable
from mcp import types
from pydantic import ValidationError
from KIDSic.dto.location import LocationQuery, LocationMetadata
from KIDSic.dto.municipality import MUNICIPALITIES, SUPPORTED_CITY_MESSAGE, supported_city_key
from KIDSic.services.interfaces.location import LocationServiceInterface
from KIDSic.api.apps.map_resource import TOOL_META

logger = logging.getLogger(__name__)


class LocationTools:
    def __init__(self, service: Callable[[], LocationServiceInterface]):
        self._service = service

    def register(self, server):
        server.list_tools()(self.list_tools)
        server.call_tool(validate_input=False)(self.call_tool)

    @staticmethod
    def _error_result(message: str) -> types.CallToolResult:
        return types.CallToolResult(
            content=[types.TextContent(type='text', text=message)], isError=True,
            _meta=TOOL_META,
        )


    async def list_tools(self):
        return [types.Tool(
            name='prikazi_vrtice', title='Prikaži vrtiće na karti',
            description=(
                'ALWAYS use this tool when the user asks to show or find '
                'kindergartens by city and optionally institution or facility name. '
                'Returns a map, cards, applied city/name and complete result counts. '
                'REQUIRES a city supplied explicitly by the user. If no city '
                'is given, ask "U kojem gradu želiš prikaz vrtića?" first. '
                'Never assume Zagreb or any other city. '
                'Only Zagreb, Varaždin and Rijeka are supported. '
                'Extract only the requested name into name, not the entire sentence. '
                'Name matching is a literal substring, ignoring case and Croatian diacritics. '
                'Omit name to show all locations in the city. '
                'Example: "Prikaži vrtić Bajka u Zagrebu" -> {"city":"Zagreb","name":"Bajka"}. '
                'If zero results are returned, ask the user to check or shorten the name; '
                'do not silently remove the name or change the city.'
            ),
            inputSchema={
                'type': 'object', 'properties': {'city': {
                    'type': 'string', 'minLength': 1, 'maxLength': 100,
                    'description': 'Podržani grad koji je korisnik izričito naveo: Zagreb, Varaždin ili Rijeka.',
                }, 'name': {
                    'type': 'string', 'maxLength': 200, 'default': '',
                    'description': 'Naziv ili dio naziva ustanove ili objekta, npr. Bajka. Prazno znači sve objekte u gradu.',
                    'examples': ['Bajka', 'Čarobna kućica'],
                }}, 'required': ['city'], 'additionalProperties': False,
            },
            outputSchema={
                'type': 'object', 'properties': {
                    'city': {'type': 'string'},
                    'name': {'type': 'string'},
                    'metadata': LocationMetadata.model_json_schema(),
                }, 'required': ['city', 'name', 'metadata'], 'additionalProperties': False,
            },
            annotations=types.ToolAnnotations(
                readOnlyHint=True, destructiveHint=False, idempotentHint=True,
                openWorldHint=False,
            ),
            _meta=TOOL_META,
        )]

    # Validation here provides the same actionable missing-city response for all
    # clients, including those which do not enforce the advertised input schema.
    async def call_tool(self, name, arguments):
        if name != 'prikazi_vrtice':
            return self._error_result('Nepoznat alat.')
        if not isinstance(arguments, dict) or 'city' not in arguments:
            return self._error_result('Grad je obavezan. Pitaj korisnika: U kojem gradu želiš prikaz vrtića?')
        if set(arguments) - {'city', 'name'}:
            return self._error_result('Za pretragu su podržani samo city (grad) i name (naziv). '
                                      'Primjer: {"city":"Zagreb","name":"Bajka"}.')
        try:
            query = LocationQuery.model_validate({'city': arguments['city'], 'q': arguments.get('name', '')})
        except ValidationError as error:
            if any(item['loc'][0] == 'q' for item in error.errors()):
                return self._error_result('Naziv (name) mora biti tekst do 200 znakova. '
                                          'Navedi samo naziv ili dio naziva; izostavi ga za sve objekte u gradu.')
            return self._error_result(f'Navedi valjan grad (1–100 znakova). {SUPPORTED_CITY_MESSAGE}')
        query = query.model_copy(update={'city': MUNICIPALITIES[supported_city_key(query.city)].name})
        try:
            locations = await self._service().list_locations(query)
        except Exception:
            logger.exception('MCP location read failed.')
            return self._error_result('Vrtići trenutačno nisu dostupni. Pokušaj ponovno kasnije.')
        name_notice = f' Naziv: „{query.q}”.' if query.q else ''
        outcome = ('Provjeri ili skrati naziv; nemoj mijenjati grad ili ukloniti naziv bez korisnikova odabira.'
                   if query.q and locations.metadata.total == 0 else 'Prikaži povezanu kartu i kartice.')
        return types.CallToolResult(
            content=[types.TextContent(type='text', text=(
                f'Prikaz vrtića za grad {query.city}: {locations.metadata.total} '
                f'rezultata, {locations.metadata.mapped} s koordinatama. '
                f'{name_notice} {outcome}'
            ))],
            structuredContent={'city': query.city, 'name': query.q,
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

