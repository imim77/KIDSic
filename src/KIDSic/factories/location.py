from KIDSic.services.concrete.location import LocationService
from KIDSic.services.interfaces.location import LocationServiceInterface


class LocationServiceFactory:
    def create(self, uow_factory) -> LocationServiceInterface:
        return LocationService(uow_factory)
