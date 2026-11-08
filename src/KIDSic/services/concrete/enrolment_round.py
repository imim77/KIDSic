"""EnrolmentRoundPresenter dates published enrolment rounds against one clock reading."""
from collections.abc import Callable
from datetime import datetime, timezone

from KIDSic.dto.location import LocationEnrolment
from KIDSic.services.interfaces.presenters import EnrolmentPresenter


class EnrolmentRoundPresenter(EnrolmentPresenter):
    # Inject the clock in tests; the status depends on the moment of the read.
    def __init__(self, clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self._clock = clock

    def present(self, rounds) -> list[LocationEnrolment]:
        now = self._clock()
        items = [LocationEnrolment.model_validate({**raw, 'status': 'dates_unknown'}) for raw in rounds]
        # A published refusal for a year outranks that year's general rounds.
        refused = {item.academic_year for item in items if not item.accepting}
        return [item.model_copy(update={'status': self._status(item, now)}) for item in items
                if not item.accepting or item.academic_year not in refused]

    @staticmethod
    def _status(item: LocationEnrolment, now: datetime) -> str:
        if not item.accepting:
            return 'not_accepting'
        if item.opens_at and now < item.opens_at:
            return 'upcoming'
        if item.closes_at and now > item.closes_at:
            return 'closed'
        # A main round without a published opening is not known to be open yet;
        # a rolling round is open during its period unless the source says otherwise.
        if item.opens_at or (item.round == 'rolling' and item.closes_at):
            return 'open'
        return 'dates_unknown'
