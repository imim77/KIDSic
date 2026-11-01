"""Explicit mappings for the three selected JSON resources, without age inference."""
import hashlib
import math
import re

from KIDSic.dto.source import KindergartenRow, name_key
from KIDSic.dto.text import normalize
from KIDSic.exceptions import SourceImportError


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


def normalize_records(records: list[dict], parser: str) -> tuple[KindergartenRow, ...]:
    if not records:
        raise SourceImportError('Empty resource refused; the last successful snapshot is preserved.')
    rows = []
    keys = set()
    for ordinal, record in enumerate(records, start=1):
        try:
            name = _text(record, 'Naziv', required=True)
            address = _text(record, 'Adresa', required=True)
            if parser == 'national':
                city = _text(record, 'Mjesto', required=True)
                identity = '|'.join((name_key(name), normalize(city), name_key(address)))
                key = hashlib.sha256(identity.encode()).hexdigest()
                row = KindergartenRow(
                    source_key=key, raw_data=record, name=name, location_name=name,
                    city=city, address=address, email=_text(record, 'ePosta'),
                    phone=_text(record, 'Telefon'), county=_text(record, 'Zupanija'),
                    postal_code=_text(record, 'PostanskiBroj'),
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
                row = KindergartenRow(
                    source_key=str(identifier).strip(), raw_data=record, name=institution,
                    location_name=name, city='Zagreb', address=address, provider_kind=provider,
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
