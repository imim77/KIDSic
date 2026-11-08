"""OtpJourneyPlanner adapts the pinned OTP 2.8.1 GTFS GraphQL plan API."""
from datetime import datetime, timezone

import httpx

from KIDSic.dto.day_route import DayPoint, Journey, RouteLeg, ZAGREB
from KIDSic.integrations.interfaces.journey import JourneyPlanner, RoutingUnavailable

QUERY = '''query DayJourney($from: InputCoordinates!, $to: InputCoordinates!,
    $date: String!, $time: String!, $modes: [TransportMode!]!) {
  plan(from: $from, to: $to, date: $date, time: $time,
       transportModes: $modes, numItineraries: 5, arriveBy: false,
       ignoreRealtimeUpdates: true) {
    itineraries { startTime endTime legs {
      mode startTime endTime from { name } to { name }
      route { shortName longName } legGeometry { points }
    } }
  }
}'''


def instant(milliseconds):
    return datetime.fromtimestamp(float(milliseconds) / 1000, timezone.utc).astimezone(ZAGREB)


class OtpJourneyPlanner(JourneyPlanner):
    def __init__(self, http: httpx.AsyncClient, endpoint: str):
        self._http = http
        self._endpoint = endpoint

    async def plan(self, origin: DayPoint, destination: DayPoint,
                   departure: datetime, mode: str) -> Journey | None:
        local = departure.astimezone(ZAGREB)
        modes = [{'mode': 'WALK'}]
        if mode == 'TRANSIT':
            modes.append({'mode': 'TRANSIT'})
        try:
            response = await self._http.post(self._endpoint, json={'query': QUERY, 'variables': {
                'from': origin.model_dump(), 'to': destination.model_dump(),
                'date': local.strftime('%Y-%m-%d'), 'time': local.strftime('%H:%M:%S'),
                'modes': modes,
            }})
            response.raise_for_status()
            payload = response.json()
            if payload.get('errors'):
                raise ValueError('OTP GraphQL error')
            journeys = [self._journey(item) for item in payload['data']['plan']['itineraries']]

            valid = [j for j in journeys if j.legs and departure <= j.departure <= j.arrival]
        except (httpx.HTTPError, ValueError, KeyError, TypeError, OverflowError) as error:
            raise RoutingUnavailable('Local OTP routing is unavailable.') from error
        return min(valid, key=lambda j: j.arrival, default=None)

    @staticmethod
    def _journey(itinerary) -> Journey:
        return Journey(departure=instant(itinerary['startTime']), arrival=instant(itinerary['endTime']),
                       legs=[OtpJourneyPlanner._leg(leg) for leg in itinerary['legs']])

    @staticmethod
    def _leg(leg) -> RouteLeg:
        route = leg.get('route') or {}
        return RouteLeg(mode=leg['mode'], departure=instant(leg['startTime']), arrival=instant(leg['endTime']),
                        from_name=leg['from']['name'], to_name=leg['to']['name'],
                        line=route.get('shortName') or route.get('longName'),
                        geometry=(leg.get('legGeometry') or {}).get('points'))
