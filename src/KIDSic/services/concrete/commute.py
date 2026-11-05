"""CommuteService asks about ambiguous addresses before ranking any journeys."""
from KIDSic.dto.commute import CommuteQuery
from KIDSic.dto.day_route import DayJourneyRequest, DayPoint
from KIDSic.integrations.interfaces.address import AddressLookup
from KIDSic.services.concrete.day_route import DayRouteService


class CommuteService:
    def __init__(self, routes: DayRouteService, addresses: AddressLookup):
        self._routes = routes
        self._addresses = addresses

    async def recommend(self, query: CommuteQuery):
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
        if unresolved:
            return {'status': 'clarification_required', 'unresolved': unresolved,
                    'notice': 'Potvrdi točnu adresu i grad ili odaberi ponuđenu lokaciju. '
                              'Ako nema podudaranja, navedi koordinate; nemoj ih nagađati.'}
        request = DayJourneyRequest(home=points['home'], work=points['work'],
            departure=query.departure, mode=query.mode, dropoff_minutes=query.dropoff_minutes, top_k=query.top_k)
        result = await self._routes.recommend(request)
        result.update(status='ok' if result['results'] else 'no_route', resolved_addresses=resolved,
                      notice='Najbolje prema dolasku na posao; nije potvrda radnog vremena, '
                             'dobne prikladnosti ni slobodnog mjesta. '
                             f'Za predaju djeteta uračunato je {query.dropoff_minutes} minuta.')
        return result
