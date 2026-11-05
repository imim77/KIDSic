from KIDSic.services.concrete.rag import RagService
from KIDSic.services.concrete.rag_evidence import RagEvidenceBuilder
from KIDSic.services.concrete.subsidy import SubsidyPolicyPresenter
from KIDSic.services.interfaces.rag import RagServiceInterface


class RagServiceFactory:
    def create(self, uow_factory) -> RagServiceInterface:
        return RagService(uow_factory, RagEvidenceBuilder(SubsidyPolicyPresenter()))
