"""Curated towns/municipalities; a settlement is linked only when the county confirms it."""
from dataclasses import dataclass

from KIDSic.dto.text import normalize


@dataclass(frozen=True)
class Municipality:
    key: str
    name: str
    county: str
    aliases: tuple[str, ...] = ()


MUNICIPALITIES = {m.key: m for m in (
    Municipality('zagreb', 'Zagreb', 'Grad Zagreb', ('zagreba', 'zagrebu')),
    Municipality('varazdin', 'Varaždin', 'Varaždinska županija', ('varazdina', 'varazdinu')),
    Municipality('rijeka', 'Rijeka', 'Primorsko-goranska županija', ('rijeke', 'rijeci')),
    Municipality('sibenik', 'Šibenik', 'Šibensko-kninska županija', ('sibenika', 'sibeniku')),
)}

SUPPORTED_CITY_MESSAGE = 'Podržani gradovi su Zagreb, Varaždin, Rijeka i Šibenik.'


def supported_city_key(value: str) -> str:
    key = normalize(value)
    for city in MUNICIPALITIES.values():
        if key == city.key or key in city.aliases:
            return city.key
    raise ValueError(SUPPORTED_CITY_MESSAGE)


def resolve_municipality(settlement: str, county: str | None) -> str | None:
    """Grad Zagreb is a single municipality; elsewhere the name must match within its county."""
    county_key = normalize(county or '')
    if county_key == 'grad zagreb':
        return 'zagreb'

    if normalize(settlement) == 'brodarica' and county_key == normalize(MUNICIPALITIES['sibenik'].county):
        return 'sibenik'
    candidate = MUNICIPALITIES.get(normalize(settlement))
    if candidate is not None and normalize(candidate.county) == county_key:
        return candidate.key
    return None
