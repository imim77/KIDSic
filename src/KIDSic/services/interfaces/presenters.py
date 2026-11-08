"""Presenter contracts turn stored rules into what parents read."""
from abc import ABC, abstractmethod

from KIDSic.dto.location import LocationEnrolment
from KIDSic.dto.subsidy import SubsidyPolicy


class SubsidyPresenter(ABC):
    @abstractmethod
    def present(self, policy: dict) -> SubsidyPolicy:
        """Return a policy's rates, conditions, reliefs and notes as text."""


class EnrolmentPresenter(ABC):
    @abstractmethod
    def present(self, rounds: list[dict]) -> list[LocationEnrolment]:
        """Return published enrolment rounds dated against the current time."""
