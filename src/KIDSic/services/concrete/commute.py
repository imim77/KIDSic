"""CommuteService asks about ambiguous addresses and kindergarten names before
ranking any journeys."""
from KIDSic.dto.commute import CommuteQuery
from KIDSic.dto.day_route import DayJourneyRequest, DayPoint
from KIDSic.integrations.interfaces.address import AddressLookup
from KIDSic.services.concrete.day_route import DayRouteService


class CommuteService:
    def __init__(self, routes: DayRouteService, addresses: AddressLookup):
        self._routes = routes
        self._addresses = addresses

    async def recommend(self, query: CommuteQuery):
        points, unresolved, resolved = self._resolve_addresses(query)
        facility_ids, names = await self._kindergartens(query.kindergartens, query.city)
        if names:
            unresolved['kindergartens'] = names
        if unresolved:
            return {'status': 'clarification_required', 'unresolved': unresolved,
                    'notice': 'Potvrdi točnu adresu i grad ili odaberi ponuđenu lokaciju. '
                              'Ako nema podudaranja, navedi koordinate; nemoj ih nagađati. '
                              'Za višeznačan vrtić neka korisnik odabere jedan od ponuđenih objekata.'}
        request = DayJourneyRequest(city=query.city, home=points['home'], work=points['work'],
            departure=query.departure, mode=query.mode, dropoff_minutes=query.dropoff_minutes, top_k=query.top_k)
        result = await self._routes.recommend(request, facility_ids)
        scope = '' if facility_ids is None else 'Uspoređeni su samo vrtići koje je korisnik naveo. '
        if query.city == 'Šibenik':
            scope += 'Usporedba ne obuhvaća sve šibenske objekte vrtića. '
        result.update(status='ok' if result['results'] else 'no_route', resolved_addresses=resolved,
                      notice=scope + 'Najbolje prema dolasku na posao; nije potvrda radnog vremena, '
                             'dobne prikladnosti ni slobodnog mjesta. '
                             f'Za predaju djeteta uračunato je {query.dropoff_minutes} minuta.')
        return result

    def _resolve_addresses(self, query: CommuteQuery):
        """_resolve_addresses accepts a point as given and an address only on
        one exact match; anything else is returned for the user to settle."""
        points, unresolved, resolved = {}, {}, {}
        for role in ('home', 'work'):
            value = getattr(query, role)
            if isinstance(value, DayPoint):
                points[role] = value
                continue
            candidates = self._addresses.find(value)
            if len(candidates) != 1 or candidates[0]['match'] != 'exact':
                unresolved[role] = {'query': value, 'candidates': candidates}
            else:
                points[role] = DayPoint(**candidates[0]['point'])
                resolved[role] = candidates[0]
        return points, unresolved, resolved

    async def _kindergartens(self, names: list[str] | None, city: str):
        """_kindergartens maps each named kindergarten to one facility. A name
        that matches several facilities, or none, is returned for the user to
        settle rather than guessed, as with addresses."""
        if names is None:
            return None, []
        facility_ids, unresolved = [], []
        for name in names:
            matches = await self._routes.find(name, city)
            if len(matches) == 1:
                facility_ids.append(str(matches[0].id))
            else:
                unresolved.append({'query': name, 'matches': len(matches), 'candidates': [
                    {'id': str(f.id), 'name': f.properties.location_name, 'address': f.properties.address}
                    for f in matches[:8]]})
        return list(dict.fromkeys(facility_ids)), unresolved
