"""Explicit mappings for the selected JSON/CSV resources, without age inference."""
import hashlib
import math
import re

from KIDSic.dto.municipality import resolve_municipality
from KIDSic.dto.source import KindergartenRow, name_key
from KIDSic.dto.text import normalize
from KIDSic.exceptions import SourceImportError

# Zagreb resources append a settlement inside the city to some addresses: "Sopnička ulica 69, Sesvete".
_ZAGREB_SETTLEMENT = re.compile(r'^(.*\d\w*)\s*,\s*([^\d,]+)$')

# These three directory entries were explicitly excluded from the kindergarten product.
_EXCLUDED_VARAZDIN_ASSOCIATIONS = {
    'udruga drustvo nasa djeca',
    'udruga drustvo sportske rekreacije sportska abeceda',
    'udruga univerzalna sportska skola junior',
}


def _text(row: dict, field: str, *, required: bool = False) -> str | None:
    value = row.get(field)
    if value is not None and not isinstance(value, str):
        raise SourceImportError(f'{field} must be text.')
    value = value.strip() if value else None
    if required and not value:
        raise SourceImportError(f'Missing required field: {field}.')
    return value or None


def _coordinate(value, maximum: int) -> float | None:
    if value is None or value == '':
        return None
    try:
        number = float(str(value).strip().replace(',', '.'))
    except ValueError as error:
        raise SourceImportError('Invalid coordinate.') from error
    if not math.isfinite(number) or abs(number) > maximum:
        raise SourceImportError('Coordinate outside its valid range.')
    return number


def _childminder_row(record: dict) -> KindergartenRow:
    name = _text(record, 'Naziv ustanove', required=True)
    address = _text(record, 'Adresa sjedišta', required=True)
    place = _text(record, 'Mjesto sjedišta', required=True)
    registry = _text(record, 'Matični broj', required=True)
    if not re.fullmatch(r'\d{8}', registry):
        raise SourceImportError('Expected an eight-digit trade registry number.')
    match = re.fullmatch(r'(\d{5})\s+(.+)', place)
    if not match or normalize(match[2]) != 'varazdin':
        raise SourceImportError('Expected a postal code and Varaždin seat settlement.')
    postal_code, settlement = match.groups()
    tax_ids = (_text(record, 'OIB') or '').split()
    if any(not re.fullmatch(r'\d{11}', value) for value in tax_ids):
        raise SourceImportError('Invalid OIB in childminder resource.')
    # Joint trades can publish multiple proprietors' OIBs; never pick one arbitrarily.
    oib = tax_ids[0] if len(set(tax_ids)) == 1 else None
    address = re.sub(r',\s*' + re.escape(settlement) + r'\s*$', '', address, flags=re.IGNORECASE)
    return KindergartenRow(
        source_key=registry, raw_data=record, name=name, location_name=name,
        settlement=settlement, address=address, postal_code=postal_code,
        scope='institution', municipality='varazdin', provider_kind='childminder',
        oib=oib, email=_text(record, 'E-mail adresa'), phone=_text(record, 'Broj telefona'),
        website_url=_text(record, 'Web/Facebook stranica'),
    )


def normalize_records(records: list[dict], parser: str) -> tuple[KindergartenRow, ...]:
    if not records:
        raise SourceImportError('Empty resource refused; the last successful snapshot is preserved.')
    rows = []
    keys = set()
    for ordinal, record in enumerate(records, start=1):
        try:
            if parser == 'varazdin-childminders':
                row = _childminder_row(record)
            else:
                name = _text(record, 'Naziv', required=True)
                address = _text(record, 'Adresa', required=True)
                if parser == 'national':
                    settlement = _text(record, 'Mjesto', required=True)
                    if (normalize(settlement) == 'varazdin'
                            and name_key(name) in _EXCLUDED_VARAZDIN_ASSOCIATIONS):
                        continue
                    county = _text(record, 'Zupanija')
                    identity = '|'.join((name_key(name), normalize(settlement), name_key(address)))
                    key = hashlib.sha256(identity.encode()).hexdigest()
                    # The MZOM directory lists legal entities; its address is the seat, not an object.
                    row = KindergartenRow(
                        source_key=key, raw_data=record, name=name, location_name=name,
                        settlement=settlement, address=address, scope='institution',
                        municipality=resolve_municipality(settlement, county),
                        email=_text(record, 'ePosta'), phone=_text(record, 'Telefon'),
                        county=county, postal_code=_text(record, 'PostanskiBroj'),
                    )
                elif parser in {'municipal', 'other'}:
                    identifier = record.get('Id')
                    if type(identifier) not in {str, int} or not str(identifier).strip():
                        raise SourceImportError('Missing resource row Id.')
                    provider = {'gradski dv': 'municipal', 'privatni dv': 'private',
                                'vjerski dv': 'religious', 'obrt za cuvanje djece': 'childminder'}.get(
                                    normalize(_text(record, 'VrstaVrtica', required=True)))
                    kind = {'maticni': 'main', 'podrucni': 'branch'}.get(
                        normalize(_text(record, 'TipVrtica', required=True)))
                    if provider is None or kind is None or (parser == 'municipal' and provider != 'municipal'):
                        raise SourceImportError('Unrecognized provider or location type.')
                    institution = re.split(r'\s*-\s*(?:matični\b|PO\b)', name, maxsplit=1,
                                           flags=re.IGNORECASE)[0].strip()
                    longitude = _coordinate(record.get('X'), 180)
                    latitude = _coordinate(record.get('Y'), 90)
                    if (longitude is None) != (latitude is None):
                        raise SourceImportError('Coordinates must be supplied together.')
                    # X/Y are published as longitude/latitude. Refuse projected/swapped
                    # coordinates instead of silently placing Zagreb objects elsewhere.
                    if longitude is not None and not (15 < longitude < 17 and 45 < latitude < 47):
                        raise SourceImportError('Coordinates do not describe the Zagreb area.')
                    settlement = 'Zagreb'
                    if match := _ZAGREB_SETTLEMENT.match(address):
                        address, settlement = match[1].strip(), match[2].strip()
                    row = KindergartenRow(
                        source_key=str(identifier).strip(), raw_data=record, name=institution,
                        location_name=name, settlement=settlement, address=address,
                        municipality='zagreb', provider_kind=provider,
                        kind=kind, district=_text(record, 'GradskaCetvrt'),
                        email=_text(record, 'Email'), phone=_text(record, 'Telefon'),
                        website_url=_text(record, 'Web'), longitude=longitude, latitude=latitude,
                    )
                else:
                    raise SourceImportError(f'Unknown parser: {parser}.')
            if row.source_key in keys:
                raise SourceImportError('Duplicate row identity in resource.')
            keys.add(row.source_key)
            rows.append(row)
        except SourceImportError as error:
            raise SourceImportError(f'{parser} row {ordinal}: {error}') from error
    return tuple(rows)
