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
    return {'city': found.pop(), 'age_months': age}
