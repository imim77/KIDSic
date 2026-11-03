"""ZagrebLocationParser maps municipal or mixed Zagreb facility resources."""
import re
from KIDSic.dto.source import KindergartenRow
from KIDSic.dto.text import normalize
from KIDSic.exceptions import SourceImportError
from KIDSic.services.interfaces.source_parser import SourceRowParser
from .fields import text, coordinate

# Zagreb resources append a settlement inside the city to some addresses: "Sopnička ulica 69, Sesvete".
_ZAGREB_SETTLEMENT = re.compile(r'^(.*\d\w*)\s*,\s*([^\d,]+)$')


class ZagrebLocationParser(SourceRowParser):
    def __init__(self, *, municipal_only: bool = False):
        self._municipal_only = municipal_only

    def parse(self, record: dict) -> KindergartenRow:
        name = text(record, 'Naziv', required=True)
        address = text(record, 'Adresa', required=True)
        identifier = record.get('Id')
        if type(identifier) not in {str, int} or not str(identifier).strip():
            raise SourceImportError('Missing resource row Id.')
        provider = {'gradski dv': 'municipal', 'privatni dv': 'private',
                    'vjerski dv': 'religious', 'obrt za cuvanje djece': 'childminder'}.get(
                        normalize(text(record, 'VrstaVrtica', required=True)))
        kind = {'maticni': 'main', 'podrucni': 'branch'}.get(
            normalize(text(record, 'TipVrtica', required=True)))
        if provider is None or kind is None or (self._municipal_only and provider != 'municipal'):
            raise SourceImportError('Unrecognized provider or location type.')
        institution = re.split(r'\s*-\s*(?:matični\b|PO\b)', name, maxsplit=1,
                               flags=re.IGNORECASE)[0].strip()
        longitude = coordinate(record.get('X'), 180)
        latitude = coordinate(record.get('Y'), 90)
        if (longitude is None) != (latitude is None):
            raise SourceImportError('Coordinates must be supplied together.')
        # X/Y are published as longitude/latitude. Refuse projected/swapped
        # coordinates instead of silently placing Zagreb objects elsewhere.
        if longitude is not None and not (15 < longitude < 17 and 45 < latitude < 47):
            raise SourceImportError('Coordinates do not describe the Zagreb area.')
        settlement = 'Zagreb'
        if match := _ZAGREB_SETTLEMENT.match(address):
            address, settlement = match[1].strip(), match[2].strip()
        return KindergartenRow(
            source_key=str(identifier).strip(), raw_data=record, name=institution,
            location_name=name, settlement=settlement, address=address,
            municipality='zagreb', provider_kind=provider,
            kind=kind, district=text(record, 'GradskaCetvrt'),
            email=text(record, 'Email'), phone=text(record, 'Telefon'),
            website_url=text(record, 'Web'), longitude=longitude, latitude=latitude,
        )
