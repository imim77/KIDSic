"""Limited deterministic Croatian parser; ambiguity requires clarification."""
import re
from KIDSic.dto.text import normalize
from KIDSic.dto.search import SearchCriteria


async def parse_request(repository, question: str) -> SearchCriteria:
    """Small deterministic Croatian example parser; ambiguous requests require clarification.

    MCP/LLM callers can supply validated city and age directly to find_options.
    """
    text = normalize(question)
    ages = re.findall(r'\b(?:od|ima)\s+(\d+)\s*(godin\w*|mjesec\w*)', text)
    if len(ages) != 1:
        raise ValueError('Navedite jednu dob djeteta u godinama ili mjesecima.')
    number, unit = ages[0]
    age = int(number) * (12 if unit.startswith('godin') else 1)
    cities = await repository.list_cities()
    found = {r['city_key'] for r in cities for alias in [r['city_key'], *r['city_aliases']]
             if re.search(r'(?<!\w)' + re.escape(normalize(alias)) + r'(?!\w)', text)}
    if len(found) != 1:
        raise ValueError('Navedite jedan grad; grad mora postojati u imeniku.')
    city = found.pop()
    areas = await repository.list_areas(city=city)
    matched = set()
    for row in areas:
        name = row['name']
        key = normalize(name)
        forms = {key}
        # Cover common feminine cases, e.g. Banfica / Banfici / Banfice.
        if key.endswith('a'):
            forms.update(key[:-1] + suffix for suffix in ('i', 'e', 'u', 'om'))
        forms.update({'centar': ('centru', 'centra'), 'durek': ('durku', 'durka'),
                      'brezje': ('brezju', 'brezja'), 'cenjavec': ('cenjavcu', 'cenjavca')}.get(key, ()))
        if any(re.search(r'(?<!\w)' + re.escape(form) + r'(?!\w)', text) for form in forms):
            matched.add(name)
    if len(matched) > 1:
        raise ValueError('Navedite jedan kvart ili naselje za pretragu.')
    criteria = {'city': city, 'age_months': age}
    if matched:
        criteria['area'] = matched.pop()
    return criteria
