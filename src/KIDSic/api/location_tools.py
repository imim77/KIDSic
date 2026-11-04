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
        filters = LocationQuery.model_json_schema()['properties']
        provider_schema = filters['provider_kind']
        return [types.Tool(
            name='prikazi_vrtice', title='Prikaži vrtiće na karti',
            description=(
                'ALWAYS use this tool when the user asks to show or find '
                'kindergartens by city, optionally name, provider type, area, child age and program. '
                'Returns a map, cards, all applied criteria and counts of confirmed and unknown suitability. '
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
                'Put one district, neighbourhood or settlement name in area, in nominative form '
                '(e.g. "na Banfici" -> "Banfica"). Area matching is exact, ignoring case and Croatian diacritics; '
                'the optional administrative prefix "Mjesni odbor " is ignored. '
                'Only attested area fields match, never addresses or facility names. Coverage is incomplete; '
                'zero matches do not mean there are no kindergartens in that area. Omit area or use "" for all areas. '
                'Convert one explicit child age to integer age_months (0–216): 2 years=24, '
                '2 years 6 months=30, 18 months=18. Never guess age from jaslice or kindergarten labels; '
                'ask for months if age is ambiguous or needed to establish age suitability. '
                'Age may be omitted/null for a general search or program-only search. '
                'Extract a requested program name into program (e.g. Montessori), not into name. '
                'Program matching is a literal substring ignoring case and Croatian diacritics. '
                'Age and program must match the SAME current sourced program for confirmed suitability. '
                'include_unknown defaults to true: unknown results are separate, not recommendations '
                'of suitability. Use false only if the user requests confirmed matches exclusively. '
                'Missing program data is not proof a program is unavailable. Confirmed suitability '
                'never guarantees a vacancy or enrolment. Do not infer programs from names, contacts or subsidy rules. '
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
                }, 'area': {
                    **filters['area'],
                    'description': 'Jedna četvrt, predio ili naselje u nominativu, npr. Banfica, '
                                   'Trešnjevka-Jug ili Zamet. Točan naziv, bez razlikovanja slova i dijakritika; '
                                   'Mjesni odbor je opcionalni prefiks. Prazno ili izostavljeno znači sva područja. '
                                   'Samo zapisi s potvrđenim područjem; pokrivenost nije potpuna.',
                }, 'age_months': {
                    **filters['age_months'],
                    'description': 'Izričito navedena dob jednog djeteta u cijelim mjesecima, 0–216; '
                                   '2 godine = 24, 2 godine i 6 mjeseci = 30. Izostavljeno/null znači bez dobnog filtra.',
                }, 'program': {
                    **filters['program'],
                    'description': 'Naziv ili dio naziva traženog programa, npr. Montessori. '
                                   'Izostavljeno/prazno znači bez filtra programa. Ne izmišljati program iz naziva vrtića.',
                }, 'include_unknown': {
                    **filters['include_unknown'],
                    'description': 'true uključuje zasebno označene nepoznate uvjete; false vraća samo '
                                   'potvrđena podudaranja dobi/programa. Bez tih filtara nema učinka.',
                }}, 'required': ['city'], 'additionalProperties': False,
            },
            outputSchema={
                'type': 'object', 'properties': {
                    'city': {'type': 'string'},
                    'name': {'type': 'string'},
                    'provider_kind': provider_schema,
                    'area': {'type': 'string'},
                    'age_months': filters['age_months'],
                    'program': {'type': 'string'},
                    'include_unknown': {'type': 'boolean'},
                    'metadata': LocationMetadata.model_json_schema(),
                }, 'required': ['city', 'name', 'provider_kind', 'area', 'age_months', 'program',
                                'include_unknown', 'metadata'], 'additionalProperties': False,
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
        if set(arguments) - {'city', 'name', 'provider_kind', 'area', 'age_months', 'program', 'include_unknown'}:
            return self._error_result('Za pretragu su podržani city (grad), name (naziv), provider_kind (vrsta), '
                                      'area (područje), age_months (dob), program i include_unknown. '
                                      'Primjer: {"city":"Zagreb","name":"Bajka"}.')
        try:
            query = LocationQuery.model_validate({'city': arguments['city'], 'q': arguments.get('name', ''),
                                                 'provider_kind': arguments.get('provider_kind'),
                                                 'area': arguments.get('area', ''),
                                                 'age_months': arguments.get('age_months'),
                                                 'program': arguments.get('program', ''),
                                                 'include_unknown': arguments.get('include_unknown', True)})
        except ValidationError as error:
            if any(item['loc'][0] == 'age_months' for item in error.errors()):
                return self._error_result('Dob (age_months) mora biti cijeli broj mjeseci od 0 do 216, '
                    'npr. 24 za 2 godine. Pitaj dob ako nije jasna. Za pretragu bez dobi izostavi parametar ili pošalji null.')
            if any(item['loc'][0] == 'program' for item in error.errors()):
                return self._error_result('Program mora biti jedan tekst do 200 znakova, npr. Montessori. '
                    'Za pretragu bez programa izostavi program ili pošalji "".')
            if any(item['loc'][0] == 'include_unknown' for item in error.errors()):
                return self._error_result('include_unknown mora biti boolean true ili false. '
                    'Pošalji true za zasebno označene nepoznate uvjete, false samo za potvrđena podudaranja.')
            if any(item['loc'][0] == 'area' for item in error.errors()):
                return self._error_result('Područje (area) mora biti jedan tekst do 200 znakova, npr. '
                    '{"city":"Varaždin","area":"Banfica"}. Za sva područja izostavi area ili pošalji "". '
                    'Za više područja prvo razjasni koje korisnik želi.')
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
        area_notice = (f' Područje: „{query.area}”. Pretraga koristi samo potvrđene nazive područja; '
                       'pokrivenost je nepotpuna. OSM nazivi nisu potvrda službenih granica.' if query.area else '')
        suitability_notice = ''
        if query.age_months is not None or query.program:
            age_notice = f'Dob: {query.age_months} mjeseci.' if query.age_months is not None else 'Dob nije zadana.'
            suitability_notice = (f' {age_notice}'
                f' Program: {query.program or "svi programi"}. Potvrđeno podudaranje: {locations.metadata.confirmed}; '
                f'uvjeti nisu potvrđeni: {locations.metadata.unknown}. '
                'Nepoznati uvjeti nisu potvrda prikladnosti. Dobna/programska prikladnost nije jamstvo mjesta ni upisa.')
        guidance = ('Provjeri ili skrati naziv. ' if query.q else '')
        guidance += ('Provjeri odabranu vrstu. ' if query.provider_kind else '')
        guidance += ('Provjeri naziv područja; nula rezultata ne znači da ondje nema vrtića. ' if query.area else '')
        guidance += ('Provjeri dob ili program; izostanak potvrde nije dokaz da program nije dostupan. '
                     if query.age_months is not None or query.program else '')
        outcome = (guidance +
                   'Nemoj mijenjati grad ili ukloniti filter bez korisnikova odabira.'
                   if (query.q or query.provider_kind or query.area or query.age_months is not None or query.program)
                   and locations.metadata.total == 0
                   else 'Prikaži povezanu kartu i kartice.')
        return types.CallToolResult(
            content=[types.TextContent(type='text', text=(
                f'Prikaz vrtića za grad {query.city}: {locations.metadata.total} '
                f'rezultata, {locations.metadata.mapped} s koordinatama. '
                f'{name_notice}{provider_notice}{area_notice}{suitability_notice} {outcome}'
            ))],
            structuredContent={'city': query.city, 'name': query.q, 'provider_kind': query.provider_kind,
                               'area': query.area,
                               'age_months': query.age_months, 'program': query.program,
                               'include_unknown': query.include_unknown,
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

