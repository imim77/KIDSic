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
    _provider_labels = {
        'municipal': 'Gradski vrtić', 'private': 'Privatni vrtić',
        'religious': 'Vjerski vrtić', 'childminder': 'Obrt za čuvanje djece',
        'other': 'Drugi pružatelj', 'unknown': 'Vrsta nije navedena',
    }

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
        provider_schema = LocationQuery.model_json_schema()['properties']['provider_kind']
        return [types.Tool(
            name='prikazi_vrtice', title='Prikaži vrtiće na karti',
            description=(
                'ALWAYS use this tool when the user asks to show or find '
                'kindergartens by city, optionally institution/facility name and provider type. '
                'Returns a map, cards, applied city/name/provider_kind and complete result counts. '
                'REQUIRES a city supplied explicitly by the user. If no city '
                'is given, ask "U kojem gradu želiš prikaz vrtića?" first. '
                'Never assume Zagreb or any other city. '
                'Only Zagreb, Varaždin and Rijeka are supported. '
                'Extract only the requested name into name, not the entire sentence. '
                'Name matching is a literal substring, ignoring case and Croatian diacritics. '
                'Omit name to match all names. '
                'Map javni/gradski to municipal, privatni to private, vjerski to religious, '
                'dadilje/obrt za čuvanje djece to childminder. '
                'Use other or unknown only when explicitly requested. '
                'Omit provider_kind or use null for all types. Select one type per call; '
                'ask which one if the user requests multiple types, do not silently drop any. '
                'Example: "Prikaži vrtić Bajka u Zagrebu" -> {"city":"Zagreb","name":"Bajka"}. '
                'Example: "Samo gradski vrtići u Zagrebu" -> {"city":"Zagreb","provider_kind":"municipal"}. '
                'If zero results are returned, report all applied criteria and ask which to change; '
                'do not silently remove any filter or change the city.'
            ),
            inputSchema={
                'type': 'object', 'properties': {'city': {
                    'type': 'string', 'minLength': 1, 'maxLength': 100,
                    'description': 'Podržani grad koji je korisnik izričito naveo: Zagreb, Varaždin ili Rijeka.',
                }, 'name': {
                    'type': 'string', 'maxLength': 200, 'default': '',
                    'description': 'Naziv ili dio naziva ustanove ili objekta, npr. Bajka. Prazno znači sve objekte u gradu.',
                    'examples': ['Bajka', 'Čarobna kućica'],
                }, 'provider_kind': {
                    **provider_schema,
                    'description': 'Jedna vrsta: municipal=javni/gradski, private=privatni, religious=vjerski, '
                                   'childminder=dadilje, other=ostali, unknown=nepoznata vrsta. '
                                   'Izostavljeno ili null znači sve vrste.',
                }}, 'required': ['city'], 'additionalProperties': False,
            },
            outputSchema={
                'type': 'object', 'properties': {
                    'city': {'type': 'string'},
                    'name': {'type': 'string'},
                    'provider_kind': provider_schema,
                    'metadata': LocationMetadata.model_json_schema(),
                }, 'required': ['city', 'name', 'provider_kind', 'metadata'], 'additionalProperties': False,
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
        if set(arguments) - {'city', 'name', 'provider_kind'}:
            return self._error_result('Za pretragu su podržani samo city (grad), name (naziv) i provider_kind (vrsta). '
                                      'Primjer: {"city":"Zagreb","name":"Bajka"}.')
        try:
            query = LocationQuery.model_validate({'city': arguments['city'], 'q': arguments.get('name', ''),
                                                 'provider_kind': arguments.get('provider_kind')})
        except ValidationError as error:
            if any(item['loc'][0] == 'provider_kind' for item in error.errors()):
                return self._error_result('Vrsta (provider_kind) mora biti jedna od: municipal (javni/gradski), '
                    'private (privatni), religious (vjerski), childminder (dadilje), other (ostali), unknown (nepoznati). '
                    'Za sve vrste izostavi parametar ili pošalji null. Za više vrsta prvo razjasni jednu vrstu.')
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
        provider_notice = f' Vrsta: {self._provider_labels[query.provider_kind]}.' if query.provider_kind else ''
        guidance = ('Provjeri ili skrati naziv. ' if query.q else '')
        guidance += ('Provjeri odabranu vrstu. ' if query.provider_kind else '')
        outcome = (guidance +
                   'Nemoj mijenjati grad ili ukloniti filter bez korisnikova odabira.'
                   if (query.q or query.provider_kind) and locations.metadata.total == 0
                   else 'Prikaži povezanu kartu i kartice.')
        return types.CallToolResult(
            content=[types.TextContent(type='text', text=(
                f'Prikaz vrtića za grad {query.city}: {locations.metadata.total} '
                f'rezultata, {locations.metadata.mapped} s koordinatama. '
                f'{name_notice}{provider_notice} {outcome}'
            ))],
            structuredContent={'city': query.city, 'name': query.q, 'provider_kind': query.provider_kind,
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

