"""RequestParser interprets Croatian criteria using caller-supplied catalogues."""
import re
from KIDSic.dto.text import normalize
from KIDSic.dto.search import SearchCriteria


class RequestParser:
    def parse_city_age(self, question: str, cities) -> SearchCriteria:
        text = normalize(question)
        ages = re.findall(r'\b(?:od|ima)\s+(\d+)\s*(godin\w*|mjesec\w*)', text)
        if len(ages) != 1:
            raise ValueError('Navedite jednu dob djeteta u godinama ili mjesecima.')
        number, unit = ages[0]
        age = int(number) * (12 if unit.startswith('godin') else 1)
        found = {r['city_key'] for r in cities for alias in [r['city_key'], *r['city_aliases']]
                 if re.search(r'(?<!\w)' + re.escape(normalize(alias)) + r'(?!\w)', text)}
        if len(found) != 1:
            raise ValueError('Navedite jedan grad; grad mora postojati u imeniku.')
        city = found.pop()
        return {'city': city, 'age_months': age}

    def parse_area(self, question: str, areas) -> str | None:
        text = normalize(question)
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
        return matched.pop() if matched else None


async def parse_request(repository, question: str) -> SearchCriteria:
    """Compatibility adapter; application services own catalogue retrieval."""
    parser = RequestParser()
    criteria = parser.parse_city_age(question, await repository.list_cities())
    area = parser.parse_area(question, await repository.list_areas(city=criteria['city']))
    if area:
        criteria['area'] = area
    return criteria
