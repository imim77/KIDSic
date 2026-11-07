"""CommuteServiceFactory wires each routed city to its local router and address index."""
import httpx

from KIDSic.config.routing import ROUTING_CITIES
from KIDSic.integrations.concrete.address import LocalAddressLookup
from KIDSic.integrations.concrete.otp import OtpJourneyPlanner
from KIDSic.services.concrete.commute import CommuteService
from KIDSic.services.concrete.day_route import DayRouteService
from KIDSic.services.interfaces.commute import CommuteServiceInterface
from KIDSic.services.interfaces.location import LocationServiceInterface


class CommuteServiceFactory:
    def create(self, locations: LocationServiceInterface,
               http: httpx.AsyncClient) -> dict[str, CommuteServiceInterface]:
        """create returns one service per city name; the caller owns http."""
        return {city.name: CommuteService(DayRouteService(locations, OtpJourneyPlanner(http, city.otp_url())),
                                          LocalAddressLookup(city.address_index(), city.name))
                for city in ROUTING_CITIES.values()}
