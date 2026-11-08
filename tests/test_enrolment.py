"""The reviewed snapshot keeps every excerpt sourced, licensed, dated and whole."""

import unittest
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from pydantic import ValidationError
from support.enrolment import CALL, DOCUMENT, ROUND

from KIDSic.config.enrolment import load_enrolment_snapshot
from KIDSic.dto.enrolment import EnrolmentDocument, EnrolmentSnapshot
from KIDSic.services.concrete.enrolment import EnrolmentDocumentService
from KIDSic.services.concrete.enrolment_round import EnrolmentRoundPresenter


class EnrolmentSnapshotTests(unittest.TestCase):
    def test_reviewed_zagreb_snapshot_is_sourced_dated_and_licensed(self):
        snapshot = load_enrolment_snapshot()
        self.assertEqual({d.municipality for d in snapshot.documents}, {"zagreb"})
        for document in snapshot.documents:
            with self.subTest(document=document.dataset_key):
                self.assertEqual(document.url.scheme, "https")
                self.assertTrue(document.license and document.license_url)
                self.assertLessEqual(document.reference_date, snapshot.verified_on)
                self.assertGreaterEqual(document.valid_until, snapshot.verified_on)
                for excerpt in document.excerpts:
                    # A passage that does not end a sentence was cut through a condition.
                    self.assertTrue(
                        excerpt.content.rstrip().endswith("."), excerpt.content[-60:]
                    )

    def test_named_excerpt_must_stay_within_the_document_scope(self):
        with self.assertRaisesRegex(ValidationError, "outside the document scope"):
            EnrolmentDocument.model_validate(
                {
                    **DOCUMENT,
                    "institutions": ["Dječji vrtić Duga"],
                    "excerpts": [
                        {
                            "content": "Predškola.",
                            "institutions": ["Dječji vrtić Bajka"],
                        }
                    ],
                }
            )

    def test_reviewed_zagreb_calls_separate_the_main_round_from_enrolment_during_the_year(
        self,
    ):
        calls = {
            c.round: c for d in load_enrolment_snapshot().documents for c in d.calls
        }
        self.assertEqual(set(calls), {"main", "rolling"})
        self.assertEqual(
            str(calls["main"].application_url), "https://eupisi.zgvrtici.hr/"
        )
        self.assertIsNone(
            calls["rolling"].opens_at
        )  # The page does not say when the year opened.

    def test_calls_need_offsets_ordered_periods_and_scoped_refusals(self):
        for invalid in (
            {"opens_at": "2026-05-13T09:00:00"},
            {"closes_at": "2026-05-01T00:00:00+02:00"},
        ):
            with self.assertRaises(ValidationError):
                EnrolmentDocument.model_validate(
                    {**DOCUMENT, "calls": [{**CALL, **invalid}]}
                )
        with self.assertRaisesRegex(ValidationError, "outside the document scope"):
            EnrolmentDocument.model_validate(
                {
                    **DOCUMENT,
                    "institutions": ["Dječji vrtić Duga"],
                    "calls": [{**CALL, "not_accepting": ["Dječji vrtić Bajka"]}],
                }
            )

    def test_rejects_inverted_period_and_repeated_sources(self):
        with self.assertRaisesRegex(ValidationError, "valid_until"):
            EnrolmentDocument.model_validate({**DOCUMENT, "valid_until": "2026-05-10"})
        with self.assertRaisesRegex(ValidationError, "own dataset_key"):
            EnrolmentSnapshot.model_validate(
                {
                    "snapshot_key": "s",
                    "verified_on": "2026-11-05",
                    "documents": [DOCUMENT, DOCUMENT],
                }
            )


class EnrolmentRoundPresenterTests(unittest.TestCase):
    def present(self, *rounds, at):
        def clock():
            return datetime.fromisoformat(at).astimezone(UTC)

        return EnrolmentRoundPresenter(clock).present(rounds)

    def test_status_follows_the_published_times_at_the_moment_of_reading(self):
        for at, status in (
            ("2026-05-13T08:59:00+02:00", "upcoming"),
            ("2026-05-13T09:00:00+02:00", "open"),
            ("2026-05-22T16:00:00+02:00", "open"),
            ("2026-05-22T16:01:00+02:00", "closed"),
        ):
            with self.subTest(at=at):
                self.assertEqual(self.present(ROUND, at=at)[0].status, status)

    def test_unknown_opening_is_open_only_for_enrolment_during_the_year(self):
        rolling = {
            **ROUND,
            "round": "rolling",
            "opens_at": None,
            "closes_at": "2027-08-31T21:59:59+00:00",
        }
        main = {**ROUND, "opens_at": None, "closes_at": None}
        statuses = [
            r.status
            for r in self.present(rolling, main, at="2026-11-05T12:00:00+01:00")
        ]
        self.assertEqual(statuses, ["open", "dates_unknown"])
        self.assertEqual(
            self.present(rolling, at="2027-09-01T00:00:00+02:00")[0].status, "closed"
        )

    def test_published_refusal_hides_the_same_years_general_rounds(self):
        rolling = {
            **ROUND,
            "round": "rolling",
            "opens_at": None,
            "closes_at": "2027-08-31T21:59:59+00:00",
        }
        refused = {**ROUND, "accepting": False}
        later = {**rolling, "academic_year": "2027./2028."}
        result = self.present(rolling, refused, later, at="2026-11-05T12:00:00+01:00")
        self.assertEqual(
            [(r.academic_year, r.status) for r in result],
            [("2026./2027.", "not_accepting"), ("2027./2028.", "open")],
        )


class EnrolmentServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_imports_every_document_in_one_unit_of_work(self):
        snapshot = EnrolmentSnapshot.model_validate(
            {
                "snapshot_key": "s",
                "verified_on": "2026-11-05",
                "documents": [DOCUMENT, {**DOCUMENT, "dataset_key": "second"}],
            }
        )
        work = SimpleNamespace(
            enrolment=SimpleNamespace(
                import_document=AsyncMock(return_value={"chunks": 2})
            )
        )
        opened = []

        @asynccontextmanager
        async def uow():
            opened.append(True)
            yield work

        result = await EnrolmentDocumentService(snapshot, uow).import_data()
        self.assertEqual((len(opened), result["chunks"]), (1, 4))
        self.assertEqual(
            EnrolmentDocumentService(snapshot).preview_import()["sources"][0][
                "excerpts"
            ],
            1,
        )
        with self.assertRaisesRegex(RuntimeError, "Unit of Work"):
            await EnrolmentDocumentService(snapshot).import_data()


if __name__ == "__main__":
    unittest.main()
