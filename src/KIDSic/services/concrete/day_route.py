"""DayRouteService ranks mapped facilities by timetable-aware arrival at work."""
import asyncio
from collections.abc import Collection
from datetime import timedelta

from KIDSic.dto.day_route import DayPoint, DayJourneyRequest
from KIDSic.config.routing import ROUTING_CITIES
from KIDSic.dto.location import LocationQuery, LocationCollection
from KIDSic.integrations.interfaces.journey import JourneyPlanner
from KIDSic.services.interfaces.location import LocationServiceInterface


class DayRouteService:
    def __init__(self, locations: LocationServiceInterface, planner: JourneyPlanner):
        self._locations = locations
        self._planner = planner

    async def _facilities(self, name: str = '', city: str = 'Rijeka'):
        coverage = ROUTING_CITIES[city]
        collection = await self._locations.list_locations(LocationQuery(city=city, q=name))
        facilities = {str(f.id): f for f in collection.features
                      if f.geometry and f.properties.location_role == 'facility'
                      and f.properties.address
                      and f.properties.city == city
                      and coverage.contains(f.geometry.coordinates[1], f.geometry.coordinates[0])}
        return collection, facilities

    async def find(self, text: str, city: str = 'Rijeka'):
        """find returns the routable facilities a user's kindergarten name
        means, using the same name search as the city map. A facility id, as
        returned with a clarification, names exactly one facility."""
        _, facilities = await self._facilities(city=city)
        if text in facilities:
            return [facilities[text]]
        _, matches = await self._facilities(text, city)
        return list(matches.values())

    async def recommend(self, request: DayJourneyRequest, facility_ids: Collection[str] | None = None):
        """recommend ranks every routable city facility, or only facility_ids
        when the user named the kindergartens to choose between."""
        collection, eligible = await self._facilities(city=request.city)
        facilities = eligible if facility_ids is None else {
            key: eligible[key] for key in facility_ids if key in eligible}
        result = await self._compare(request, list(facilities.values()))
        reachable = [r for r in result['results'] if r['status'] == 'ok']
        selected = reachable[:request.top_k]
        locations = LocationCollection(features=[facilities[r['facility_id']] for r in selected],
            metadata={'total': len(selected), 'mapped': len(selected), 'unmapped': 0, 'scope': 'city'})
        result.update(results=selected, top_k=request.top_k,
                      locations=locations.model_dump(mode='json'), searched=len(facilities),
                      reachable=len(reachable), without_route=len(facilities) - len(reachable),
                      # Named kindergartens were resolved among routable ones.
                      excluded=collection.metadata.total - len(eligible) if facility_ids is None else 0,
                      scope='all' if facility_ids is None else 'selected',
                      ranking='earliest_arrival_at_work', city=request.city,
                      home=request.home.model_dump(), work=request.work.model_dump(),
                      mode=request.mode)
        return result

    async def _compare(self, request: DayJourneyRequest, facilities):
        baseline = await self._planner.plan(request.home, request.work,
                                            request.departure, request.mode)
        semaphore = asyncio.Semaphore(4)

        async def through(facility):
            # Bound concurrent routing work even when ranking every city facility.
            async with semaphore:
                lon, lat = facility.geometry.coordinates
                point = DayPoint(lat=lat, lon=lon)
                first = await self._planner.plan(request.home, point, request.departure, request.mode)
                second = None if first is None else await self._planner.plan(
                    point, request.work, first.arrival + timedelta(minutes=request.dropoff_minutes),
                    request.mode)
                result = {'facility_id': str(facility.id), 'name': facility.properties.location_name,
                          'address': facility.properties.address, 'opening_hours': None,
                          'point': point.model_dump(), 'status': 'ok' if second else 'no_route'}
                if second:
                    elapsed = int((second.arrival - request.departure).total_seconds())
                    direct = None if baseline is None else int(
                        (baseline.arrival - request.departure).total_seconds())
                    journeys = [first, second]
                    transfers = sum(max(0, sum(leg.mode != 'WALK' for leg in j.legs) - 1)
                                    for j in journeys)
                    result.update(arrival=second.arrival.isoformat(), elapsed_seconds=elapsed,
                        extra_seconds=None if direct is None else elapsed - direct,
                        transfers=transfers, journeys=[j.model_dump(mode='json') for j in journeys])
                return result

        tasks = [asyncio.create_task(through(f)) for f in facilities]
        try:
            results = await asyncio.gather(*tasks)
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        results.sort(key=lambda item: (item.get('elapsed_seconds', float('inf')), item['facility_id']))
        city = ROUTING_CITIES[request.city]
        return {'results': results, 'baseline': baseline.model_dump(mode='json') if baseline else None,
                'departure': request.departure.isoformat(), 'dropoff_minutes': request.dropoff_minutes,
                'sources': {'router': 'OpenTripPlanner 2.8.1', 'gtfs_sha256': city.gtfs_sha256,
                            'gtfs_url': city.gtfs_url, 'publisher': city.publisher, 'license': city.license,
                            'license_url': city.license_url, 'retrieved_on': str(city.retrieved_on),
                            'service_start': str(city.service_start), 'service_end': str(city.service_end),
                            'timetable': 'scheduled', 'timezone': 'Europe/Zagreb',
                            'opening_hours': 'unverified'}}
