"""RijekaLocationParser maps published facilities to their parent institutions."""
import hashlib

from KIDSic.dto.source import KindergartenRow, name_key
from KIDSic.dto.text import normalize
from KIDSic.exceptions import SourceImportError
from KIDSic.services.interfaces.source_parser import SourceRowParser
from .fields import text

_DIRECTORY = 'https://data.rijeka.hr/dataset/djecji-vrtici'
# The national directory includes the pedagogical qualifier in this legal name.
_PARENT_NAMES = {'dv mala vila': 'Dječji vrtić "Mala Vila", waldorfski'}
_FOUNDERS = {
    'grad rijeka': 'municipal',
    'druzba sestara presvetog srca isusova': 'religious',
    'druzba sestara milosrdnica sv. vinka paulskoga': 'religious',
    'udruga gradana drustvo prijatelja waldorfske pedagogije': 'private',
    'ines zic': 'private',
    'barbara drezga': 'private',
    'sandra cikac stjepic': 'private',
    'marija simunovic': 'private',
    'dolores matkovic': 'private',
    'alida diminic i marko malobabic': 'private',
}


class RijekaLocationParser(SourceRowParser):
    def parse(self, record: dict) -> KindergartenRow:
        ordinal = text(record, 'RBR', required=True)
        if not ordinal.isascii() or not ordinal.isdigit() or int(ordinal) < 1:
            raise SourceImportError('Expected a positive Rijeka row number.')
        facility = text(record, 'Vrtić', required=True)
        address = text(record, 'Adresa', required=True)
        parent = text(record, 'Centar', required=True)
        text(record, 'Adresa centra', required=True)
        founder = text(record, 'Osnivač', required=True)
        if name_key(parent) == 'kbc rijeka':
            # Grad Rijeka confirms DV Rijeka operates at KBC Kantrida; it is
            # not a separate kindergarten institution despite this CSV label.
            if name_key(facility) != 'kbc rijeka' or normalize(founder) != 'grad rijeka':
                raise SourceImportError('Review the changed KBC Rijeka parent institution.')
            parent = 'Dječji vrtić Rijeka'
        parent = _PARENT_NAMES.get(name_key(parent), parent)
        provider = _FOUNDERS.get(normalize(founder), 'unknown')
        # RBR is an ordinal, not a registry ID. Address edits and reordering
        # must retain the facility's source identity.
        identity = '|'.join((name_key(parent), name_key(facility)))
        return KindergartenRow(
            source_key=hashlib.sha256(identity.encode()).hexdigest(), raw_data=record,
            name=parent, location_name=f'{parent} — {facility}',
            settlement='Rijeka', address=address, municipality='rijeka',
            county='Primorsko-goranska županija', provider_kind=provider,
            provider_kind_source_url=_DIRECTORY if provider != 'unknown' else None,
        )
