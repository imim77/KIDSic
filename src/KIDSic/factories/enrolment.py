from KIDSic.config.enrolment import load_enrolment_snapshot
from KIDSic.services.concrete.enrolment import EnrolmentDocumentService


class EnrolmentDocumentServiceFactory:
    def create(self, uow_factory=None):
        return EnrolmentDocumentService(load_enrolment_snapshot(), uow_factory)
