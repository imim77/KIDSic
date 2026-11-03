"""NationalDirectoryParser maps legal entities and explicit exclusions."""
import hashlib
from KIDSic.dto.municipality import resolve_municipality
from KIDSic.dto.source import KindergartenRow, name_key
from KIDSic.dto.text import normalize
from KIDSic.services.interfaces.source_parser import SourceRowParser
from .fields import text

# These three directory entries were explicitly excluded from the kindergarten product.
_EXCLUDED_VARAZDIN_ASSOCIATIONS = {
    'udruga drustvo nasa djeca',
    'udruga drustvo sportske rekreacije sportska abeceda',
    'udruga univerzalna sportska skola junior',
}


class NationalDirectoryParser(SourceRowParser):
    def parse(self, record: dict) -> KindergartenRow | None:
        name = text(record, 'Naziv', required=True)
        address = text(record, 'Adresa', required=True)
        settlement = text(record, 'Mjesto', required=True)
        if (normalize(settlement) == 'varazdin'
                and name_key(name) in _EXCLUDED_VARAZDIN_ASSOCIATIONS):
            return None
        county = text(record, 'Zupanija')
        identity = '|'.join((name_key(name), normalize(settlement), name_key(address)))
        key = hashlib.sha256(identity.encode()).hexdigest()
        # The MZOM directory lists legal entities; its address is the seat, not an object.
        return KindergartenRow(
            source_key=key, raw_data=record, name=name, location_name=name,
            settlement=settlement, address=address, scope='institution',
            municipality=resolve_municipality(settlement, county),
            email=text(record, 'ePosta'), phone=text(record, 'Telefon'),
            county=county, postal_code=text(record, 'PostanskiBroj'),
        )
