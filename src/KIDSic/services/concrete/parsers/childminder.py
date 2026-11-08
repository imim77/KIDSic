"""ChildminderDirectoryParser preserves registry identity and joint-trade OIBs."""
import re
from KIDSic.dto.source import KindergartenRow
from KIDSic.dto.text import normalize
from KIDSic.exceptions import SourceImportError
from KIDSic.services.interfaces.source_parser import SourceRowParser
from .fields import text


class ChildminderDirectoryParser(SourceRowParser):
    def parse(self, record: dict) -> KindergartenRow:
        name = text(record, 'Naziv ustanove', required=True)
        address = text(record, 'Adresa sjedišta', required=True)
        place = text(record, 'Mjesto sjedišta', required=True)
        registry = text(record, 'Matični broj', required=True)
        if not re.fullmatch(r'\d{8}', registry):
            raise SourceImportError('Expected an eight-digit trade registry number.')
        match = re.fullmatch(r'(\d{5})\s+(.+)', place)
        if not match or normalize(match[2]) != 'varazdin':
            raise SourceImportError('Expected a postal code and Varaždin seat settlement.')
        postal_code, settlement = match.groups()
        tax_ids = (text(record, 'OIB') or '').split()
        if any(not re.fullmatch(r'\d{11}', value) for value in tax_ids):
            raise SourceImportError('Invalid OIB in childminder resource.')

        oib = tax_ids[0] if len(set(tax_ids)) == 1 else None
        address = re.sub(r',\s*' + re.escape(settlement) + r'\s*$', '', address, flags=re.IGNORECASE)
        return KindergartenRow(
            source_key=registry, raw_data=record, name=name, location_name=name,
            settlement=settlement, address=address, postal_code=postal_code,
            scope='institution', municipality='varazdin', provider_kind='childminder',
            oib=oib, email=text(record, 'E-mail adresa'), phone=text(record, 'Broj telefona'),
            website_url=text(record, 'Web/Facebook stranica'),
        )

