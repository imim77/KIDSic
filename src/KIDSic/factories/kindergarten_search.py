from KIDSic.services.concrete.kindergarten_search import KindergartenSearchService
from KIDSic.services.interfaces.kindergarten_search import KindergartenSearchServiceInterface


class KindergartenSearchServiceFactory:
    def create(self, uow_factory) -> KindergartenSearchServiceInterface:
        return KindergartenSearchService(uow_factory)
