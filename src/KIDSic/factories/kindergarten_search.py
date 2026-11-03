from KIDSic.db.uow.base import UnitOfWorkFactory
from KIDSic.services.concrete.request_parser import RequestParser
from KIDSic.services.concrete.kindergarten_search import KindergartenSearchService
from KIDSic.services.interfaces.kindergarten_search import KindergartenSearchServiceInterface


class KindergartenSearchServiceFactory:
    def create(self, uow_factory: UnitOfWorkFactory) -> KindergartenSearchServiceInterface:
        return KindergartenSearchService(uow_factory, RequestParser())
