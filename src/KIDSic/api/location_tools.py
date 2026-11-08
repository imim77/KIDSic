"""LocationTools translates MCP calls into location-service requests."""
import base64
import gzip
import logging
from collections.abc import Callable
from mcp import types
from pydantic import ValidationError
from KIDSic.api.tool_results import text_error
from KIDSic.dto.location import LocationCollection, LocationQuery, LocationMetadata
from KIDSic.dto.municipality import MUNICIPALITIES, SUPPORTED_CITY_MESSAGE, supported_city_key
from KIDSic.services.interfaces.location import LocationServiceInterface
from KIDSic.api.apps.map_resource import TOOL_META

logger = logging.getLogger(__name__)

INVALID_NEARBY = ('near mora biti [dužina, širina] u WGS84, a radius_m cijeli broj metara '
    'od 1 do 50000; šalju se zajedno, npr. {"city":"Zagreb","near":[15.9775,45.8131],"radius_m":1000}. '
    'Ne procjenjuj koordinate iz adrese; zamoli korisnika da odabere točku na karti. '
    'Za pretragu bez radijusa izostavi oba parametra.')
INVALID_FIELDS = {
    'area': 'Područje (area) mora biti jedan tekst do 200 znakova, npr. '
            '{"city":"Varaždin","area":"Banfica"}. Za sva područja izostavi area ili pošalji "". '
            'Za više područja prvo razjasni koje korisnik želi.',
    'provider_kind': 'Vrsta (provider_kind) mora biti jedna od: municipal (javni/gradski), '
                     'private (privatni), religious (vjerski), childminder (dadilje), other (ostali), '
                     'unknown (nepoznati). Za sve vrste izostavi parametar ili pošalji null. '
                     'Za više vrsta prvo razjasni jednu vrstu.',
    'q': 'Naziv (name) mora biti tekst do 200 znakova. '
         'Navedi samo naziv ili dio naziva; izostavi ga za sve objekte u gradu.',
}


class LocationTools:
    name = 'prikazi_vrtice'
    _arguments = {'city', 'name', 'provider_kind', 'area', 'near', 'radius_m'}
    _provider_labels = {
        'municipal': 'Gradski vrtić', 'private': 'Privatni vrtić',
        'religious': 'Vjerski vrtić', 'childminder': 'Obrt za čuvanje djece',
        'other': 'Drugi pružatelj', 'unknown': 'Vrsta nije navedena',
    }

    def __init__(self, service: Callable[[], LocationServiceInterface]):
        self._service = service

    async def list_tools(self):
        filters = LocationQuery.model_json_schema()['properties']
        provider_schema = filters['provider_kind']
        return [types.Tool(
            name=self.name, title='Prikaži vrtiće na karti',
            description=(
                'For home-to-work commute recommendations use KIDSic:preporuci_vrtice_usput instead. '
                'For general city searches, ALWAYS use this tool when the user asks to show or find '
                'kindergartens by city, optionally name, provider type, area. '
                'Returns a map, cards, all applied criteria and location counts. '
                'REQUIRES a city supplied explicitly by the user. If no city '
                'is given, ask "U kojem gradu želiš prikaz vrtića?" first. '
                'Never assume Zagreb or any other city. '
                'Only Zagreb, Varaždin, Rijeka and Šibenik are supported. '
                'Extract only the requested name into name, not the entire sentence. '
                'Name matching is a literal substring, ignoring case and Croatian diacritics. '
                'Omit name to match all names. '
                'Map javni/gradski to municipal, privatni to private, vjerski to religious, '
                'dadilje/obrt za čuvanje djece to childminder. '
                'Use other or unknown only when explicitly requested. '
                'Omit provider_kind or use null for all types. Select one type per call; '
                'ask which one if the user requests multiple types, do not silently drop any. '
                'Put one district, neighbourhood or settlement name in area, in nominative form '
                '(e.g. "na Banfici" -> "Banfica"). Area matching is exact, ignoring case and Croatian diacritics; '
                'the optional administrative prefix "Mjesni odbor " is ignored. '
                'Only attested area fields match, never addresses or facility names. Coverage is incomplete; '
                'zero matches do not mean there are no kindergartens in that area. Omit area or use "" for all areas. '
                'near ([longitude, latitude] in WGS84) with radius_m (integer metres, 1–50000) limits results '
                'to a straight-line radius; both or neither. Use only coordinates chosen in the map UI or '
                'given explicitly by the user as numbers. NEVER estimate coordinates from an address or place '
                'name; ask the user to choose the point on the map instead. Distance is not travel time. '
                'Objects without verified coordinates are excluded from a radius search; results come nearest first. '
                'For a follow-up, send all criteria the user wants to retain, changing or clearing only '
                'what they requested. Reuse an explicitly established city only when unambiguous; '
                'ask otherwise. Each call is a full search, not a patch of the previous call. '
                'Example: "Prikaži vrtić Bajka u Zagrebu" -> {"city":"Zagreb","name":"Bajka"}. '
                'Example: "Samo gradski vrtići u Zagrebu" -> {"city":"Zagreb","provider_kind":"municipal"}. '
                'Example: "Vrtići na Banfici u Varaždinu" -> {"city":"Varaždin","area":"Banfica"}. '
                'If zero results are returned, report all applied criteria and ask which to change; '
                'do not silently remove any filter or change the city.'
            ),
            inputSchema={
                'type': 'object', 'properties': {'city': {
                    'type': 'string', 'minLength': 1, 'maxLength': 100,
                    'description': 'Podržani grad koji je korisnik izričito naveo: Zagreb, Varaždin, Rijeka ili Šibenik.',
                }, 'name': {
                    'type': 'string', 'maxLength': 200, 'default': '',
                    'description': 'Naziv ili dio naziva ustanove ili objekta, npr. Bajka. Prazno znači sve objekte u gradu.',
                    'examples': ['Bajka', 'Čarobna kućica'],
                }, 'provider_kind': {
                    **provider_schema,
                    'description': 'Jedna vrsta: municipal=javni/gradski, private=privatni, religious=vjerski, '
                                   'childminder=dadilje, other=ostali, unknown=nepoznata vrsta. '
                                   'Izostavljeno ili null znači sve vrste.',
                }, 'area': {
                    **filters['area'],
                    'description': 'Jedna četvrt, predio ili naselje u nominativu, npr. Banfica, '
                                   'Trešnjevka-Jug ili Zamet. Točan naziv, bez razlikovanja slova i dijakritika; '
                                   'Mjesni odbor je opcionalni prefiks. Prazno ili izostavljeno znači sva područja. '
                                   'Samo zapisi s potvrđenim područjem; pokrivenost nije potpuna.',
                }, 'near': {
                    'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 2,
                    'description': 'Točka [dužina, širina] u WGS84 iz karte ili izričito od korisnika; '
                                   'nikad procijenjena iz adrese ili naziva mjesta. Šalje se zajedno s radius_m.',
                }, 'radius_m': {
                    **filters['radius_m'],
                    'description': 'Zračni radijus u cijelim metrima, 1–50000, npr. 1000. Šalje se zajedno s near.',
                }}, 'required': ['city'], 'additionalProperties': False,
            },
            outputSchema={
                'type': 'object', 'properties': {
                    'city': {'type': 'string'},
                    'name': {'type': 'string'},
                    'provider_kind': provider_schema,
                    'area': {'type': 'string'},
                    'near': {'anyOf': [{'type': 'array', 'items': {'type': 'number'}}, {'type': 'null'}]},
                    'radius_m': filters['radius_m'],
                    'metadata': LocationMetadata.model_json_schema(),
                }, 'required': ['city', 'name', 'provider_kind', 'area', 'near', 'radius_m', 'metadata'], 'additionalProperties': False,
            },
            annotations=types.ToolAnnotations(
                readOnlyHint=True, destructiveHint=False, idempotentHint=True,
                openWorldHint=False,
            ),
            _meta=TOOL_META,
        )]



    async def call_tool(self, name, arguments):
        if name != self.name:
            return text_error('Nepoznat alat.', TOOL_META)
        if not isinstance(arguments, dict) or 'city' not in arguments:
            return text_error('Grad je obavezan. Pitaj korisnika: U kojem gradu želiš prikaz vrtića?', TOOL_META)
        if set(arguments) - self._arguments:
            return text_error('Za pretragu su podržani city (grad), name (naziv), provider_kind (vrsta), '
                              'area (područje), near i radius_m. '
                              'Primjer: {"city":"Zagreb","name":"Bajka"}.', TOOL_META)
        try:
            query = self._query(arguments)
        except ValidationError as error:
            return text_error(self._invalid_message(error), TOOL_META)
        try:
            locations = await self._service().list_locations(query)
        except Exception:
            logger.exception('MCP location read failed.')
            return text_error('Vrtići trenutačno nisu dostupni. Pokušaj ponovno kasnije.', TOOL_META)
        return types.CallToolResult(
            content=[types.TextContent(type='text', text=self._summary(query, locations))],
            structuredContent=self._criteria(query, locations),
            _meta={**TOOL_META, 'locations': self._encoded(locations)},
        )

    @staticmethod
    def _query(arguments: dict) -> LocationQuery:
        """_query maps tool arguments onto the shared search query, naming the
        supported city as the catalogue spells it."""
        near = arguments.get('near')

        if near is not None and (not isinstance(near, list) or not all(
                isinstance(value, (int, float)) and not isinstance(value, bool) for value in near)):
            near = 'invalid'
        query = LocationQuery.model_validate({'city': arguments['city'], 'q': arguments.get('name', ''),
                                              'provider_kind': arguments.get('provider_kind'),
                                              'area': arguments.get('area', ''), 'near': near,
                                              'radius_m': arguments.get('radius_m')})
        return query.model_copy(update={'city': MUNICIPALITIES[supported_city_key(query.city)].name})

    @staticmethod
    def _invalid_message(error: ValidationError) -> str:
        """_invalid_message explains the first invalid criterion, checking the
        point search first because a model most often guesses coordinates."""
        fields = [item['loc'][0] if item['loc'] else None for item in error.errors()]
        if any(field in (None, 'near', 'radius_m') for field in fields):
            return INVALID_NEARBY
        return next((INVALID_FIELDS[field] for field in ('area', 'provider_kind', 'q') if field in fields),
                    f'Navedi valjan grad (1–100 znakova). {SUPPORTED_CITY_MESSAGE}')

    def _summary(self, query: LocationQuery, locations: LocationCollection) -> str:
        """_summary tells the model what was searched and how to present it."""
        notices = ''
        if query.q:
            notices += f' Naziv: „{query.q}”.'
        if query.provider_kind:
            notices += f' Vrsta: {self._provider_labels[query.provider_kind]}.'
        if query.area:
            notices += (f' Područje: „{query.area}”. Pretraga koristi samo potvrđene nazive područja; '
                        'pokrivenost je nepotpuna. OSM nazivi nisu potvrda službenih granica.')
        if query.near is not None:
            notices += (f' Zračno do {query.radius_m} m od točke {query.near[0]}, {query.near[1]}; '
                        'samo objekti s potvrđenim koordinatama, poredani od najbližeg. '
                        'Udaljenost nije vrijeme putovanja.')
        return (f'Prikaz vrtića za grad {query.city}: {locations.metadata.total} '
                f'rezultata, {locations.metadata.mapped} s koordinatama. '
                f'{notices} {self._outcome(query, locations)}')

    @staticmethod
    def _outcome(query: LocationQuery, locations: LocationCollection) -> str:
        """_outcome asks the model to keep a filtered empty search intact."""
        filtered = query.q or query.provider_kind or query.area or query.near is not None
        if not filtered or locations.metadata.total:
            return 'Prikaži povezanu kartu i kartice.'
        guidance = ('Provjeri ili skrati naziv. ' if query.q else '')
        guidance += ('Provjeri odabranu vrstu. ' if query.provider_kind else '')
        guidance += ('Provjeri naziv područja; nula rezultata ne znači da ondje nema vrtića. ' if query.area else '')
        guidance += ('Predloži veći radijus ili drugu točku. ' if query.near is not None else '')
        return guidance + 'Nemoj mijenjati grad ili ukloniti filter bez korisnikova odabira.'

    @staticmethod
    def _criteria(query: LocationQuery, locations: LocationCollection) -> dict:
        return {'city': query.city, 'name': query.q, 'provider_kind': query.provider_kind,
                'area': query.area, 'near': list(query.near) if query.near is not None else None,
                'radius_m': query.radius_m, 'metadata': locations.metadata.model_dump(mode='json')}



    @staticmethod
    def _encoded(locations: LocationCollection) -> dict:
        data = gzip.compress(locations.model_dump_json().encode('utf-8'), mtime=0)
        return {'encoding': 'gzip+base64', 'data': base64.b64encode(data).decode('ascii')}
