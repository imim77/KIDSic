"""DayRouteService ranks mapped facilities by timetable-aware arrival at work."""
import asyncio
from collections.abc import Collection
from datetime import timedelta

from KIDSic.dto.day_route import (DayPoint, DayJourneyRequest,
    GTFS_SHA256, GTFS_URL, SERVICE_START, SERVICE_END)
from KIDSic.dto.location import LocationQuery, LocationCollection
from KIDSic.integrations.interfaces.journey import JourneyPlanner
from KIDSic.services.interfaces.location import LocationServiceInterface


class DayRouteService:
    def __init__(self, locations: LocationServiceInterface, planner: JourneyPlanner):
        self._locations = locations
        self._planner = planner

    async def _facilities(self, name: str = ''):
        collection = await self._locations.list_locations(LocationQuery(city='Rijeka', q=name))
        facilities = {str(f.id): f for f in collection.features
                      if f.geometry and f.properties.location_role == 'facility'
                      and f.properties.address
                      and 14.20 <= f.geometry.coordinates[0] <= 14.65
                      and 45.20 <= f.geometry.coordinates[1] <= 45.45}
        return collection, facilities

    async def find(self, text: str):
        """find returns the routable facilities a user's kindergarten name
        means, using the same name search as the city map. A facility id, as
        returned with a clarification, names exactly one facility."""
        _, facilities = await self._facilities()
        if text in facilities:
            return [facilities[text]]
        _, matches = await self._facilities(text)
        return list(matches.values())

    async def recommend(self, request: DayJourneyRequest, facility_ids: Collection[str] | None = None):
        """recommend ranks every routable Rijeka facility, or only facility_ids
        when the user named the kindergartens to choose between."""
        collection, eligible = await self._facilities()
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
                      ranking='earliest_arrival_at_work', city='Rijeka',
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
        return {'results': results, 'baseline': baseline.model_dump(mode='json') if baseline else None,
                'departure': request.departure.isoformat(), 'dropoff_minutes': request.dropoff_minutes,
                'sources': {'router': 'OpenTripPlanner 2.8.1', 'gtfs_sha256': GTFS_SHA256,
                            'gtfs_url': GTFS_URL, 'publisher': 'vekejsn', 'license': 'CC-BY-4.0',
                            'service_start': str(SERVICE_START), 'service_end': str(SERVICE_END),
                            'timetable': 'scheduled', 'timezone': 'Europe/Zagreb',
                            'opening_hours': 'unverified'}}
