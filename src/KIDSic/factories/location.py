from KIDSic.db.uow.base import UnitOfWorkFactory
from KIDSic.services.concrete.location import LocationService
from KIDSic.services.concrete.subsidy import SubsidyPolicyPresenter
from KIDSic.services.interfaces.location import LocationServiceInterface


class LocationServiceFactory:
    def create(self, uow_factory: UnitOfWorkFactory) -> LocationServiceInterface:
        return LocationService(uow_factory, SubsidyPolicyPresenter())
