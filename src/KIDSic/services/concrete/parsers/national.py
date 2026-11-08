"""NationalDirectoryParser maps legal entities and explicit exclusions."""
import hashlib
from KIDSic.dto.municipality import resolve_municipality
from KIDSic.dto.source import KindergartenRow, name_key
from KIDSic.dto.text import normalize
from KIDSic.services.interfaces.source_parser import SourceRowParser
from .fields import text


_EXCLUDED_VARAZDIN_ASSOCIATIONS = {
    'udruga drustvo nasa djeca',
    'udruga drustvo sportske rekreacije sportska abeceda',
    'udruga univerzalna sportska skola junior',
}

_VARAZDIN_DIRECTORY = 'https://varazdin.hr/djecji-vrtici/'
_VARAZDIN_BUDGET = ('https://varazdin.hr/upload/2024/11/'
                   'obrazlozenje_nacrta_proracuna_2025-2027_-_672b9864ddddb.pdf')
_ZAGREB_DIRECTORY = ('https://www.zagreb.hr/UserDocsImages/arhiva/odgoj_obrazovanje_spot/'
                    'POPIS%20VJERSKIH%20I%20PRIVATNIH%20DV_ZA%20WEB_kris.pdf')

_REVIEWED_PROVIDERS = {
    'varazdin': {
        'dv varazdin': ('municipal', _VARAZDIN_DIRECTORY),
        'dv bajka': ('private', _VARAZDIN_DIRECTORY),
        'dv djecji svijet': ('private', _VARAZDIN_DIRECTORY),
        'dv malo drvo': ('private', _VARAZDIN_BUDGET),
        'dv pinokio': ('private', _VARAZDIN_DIRECTORY),
        'dv sreca': ('private', _VARAZDIN_BUDGET),
        'dv vrtic panda': ('private', _VARAZDIN_BUDGET),
        'dv zecic': ('private', _VARAZDIN_DIRECTORY),
        'dv zeko': ('private', _VARAZDIN_DIRECTORY),
        'dv cira cara': ('private', _VARAZDIN_DIRECTORY),
        'dv sveta ursula': ('religious', _VARAZDIN_DIRECTORY),
    },
    'zagreb': {
        'dv carobna kucica': ('private', _ZAGREB_DIRECTORY),
        'dv cvjetnjak': ('religious', _ZAGREB_DIRECTORY),
        'dv drvo znanja': ('private', 'https://tltkindergarten.com/hr/'),
        'dv mali cvrcak': ('private', _ZAGREB_DIRECTORY),
        'dv mudre glavice': ('private', _ZAGREB_DIRECTORY),
        'dv ruzicnjak': ('private', 'https://rino-institut.hr/ruzicnjak-klinci-rinci/'),
        'dv zvjezdica': ('private', 'https://cas.hr/vrtic/'),
        'dv andela merici': ('religious', _ZAGREB_DIRECTORY),
        'dv frfi': ('private', _ZAGREB_DIRECTORY),
        'dv mirjam weiller': ('religious', _ZAGREB_DIRECTORY),
        'dv vitica': ('private', _ZAGREB_DIRECTORY),
    },
}
_OTHER_PROVIDERS = (
    'drustvo ', 'glazbaonica ', 'hrvatski skijaski klub ', 'institut ',
    'judo klub ', 'klizacko koturaljkaski klub ', 'kosarkaski klub ',
    'kraci program ', 'kreativna udruga ', 'muski rukometni klub ',
    'plesna udruga ', 'plesni studio ', 'program ', 'ritmicko plesna udruga ',
    'sportska udruga ', 'sportsko ', 'sportski ', 'studio ', 'taekwondo klub ',
    'tenis klub ', 'tjelovjezbeno drustvo ', 'tkd ', 'udruga ', 'uduga ',
    'univerzalna sportska skola ', 'ustanova upravljanje sportskim objektima',
)


class NationalDirectoryParser(SourceRowParser):
    def parse(self, record: dict) -> KindergartenRow | None:
        name = text(record, 'Naziv', required=True)
        address = text(record, 'Adresa', required=True)
        settlement = text(record, 'Mjesto', required=True)
        if (normalize(settlement) == 'varazdin'
                and name_key(name) in _EXCLUDED_VARAZDIN_ASSOCIATIONS):
            return None
        county = text(record, 'Zupanija')
        municipality = resolve_municipality(settlement, county)
        provider, provider_url = _REVIEWED_PROVIDERS.get(municipality, {}).get(
            name_key(name), ('unknown', None))
        if (municipality in _REVIEWED_PROVIDERS and provider == 'unknown'
                and name_key(name).startswith(_OTHER_PROVIDERS)):
            provider = 'other'
        identity = '|'.join((name_key(name), normalize(settlement), name_key(address)))
        key = hashlib.sha256(identity.encode()).hexdigest()

        return KindergartenRow(
            source_key=key, raw_data=record, name=name, location_name=name,
            settlement=settlement, address=address, scope='institution',
            municipality=municipality, provider_kind=provider,
            provider_kind_source_url=provider_url,
            email=text(record, 'ePosta'), phone=text(record, 'Telefon'),
            county=county, postal_code=text(record, 'PostanskiBroj'),
        )
