"""The reviewed snapshot keeps every excerpt sourced, licensed, dated and whole."""
import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

from pydantic import ValidationError

from KIDSic.config.enrolment import load_enrolment_snapshot
from KIDSic.dto.enrolment import EnrolmentDocument, EnrolmentSnapshot
from KIDSic.services.concrete.enrolment import EnrolmentDocumentService

DOCUMENT = dict(dataset_key='example-enrolment', title='Obavijest o upisu', publisher='Grad Zagreb',
    url='https://example.invalid/upis.pdf', license='Ponovna uporaba uz navođenje izvora',
    license_url='https://example.invalid/uvjeti', municipality='zagreb', provider_kinds=['municipal'],
    reference_date='2026-05-11', date_kind='published', valid_until='2027-08-31',
    excerpts=[{'content': 'Zahtjevi se podnose od 13. svibnja 2026. do 22. svibnja 2026.'}])


class EnrolmentSnapshotTests(unittest.TestCase):
    def test_reviewed_zagreb_snapshot_is_sourced_dated_and_licensed(self):
        snapshot = load_enrolment_snapshot()
        self.assertEqual({d.municipality for d in snapshot.documents}, {'zagreb'})
        for document in snapshot.documents:
            with self.subTest(document=document.dataset_key):
                self.assertEqual(document.url.scheme, 'https')
                self.assertTrue(document.license and document.license_url)
                self.assertLessEqual(document.reference_date, snapshot.verified_on)
                self.assertGreaterEqual(document.valid_until, snapshot.verified_on)
                for excerpt in document.excerpts:
                    # A passage that does not end a sentence was cut through a condition.
                    self.assertTrue(excerpt.content.rstrip().endswith('.'), excerpt.content[-60:])

    def test_named_excerpt_must_stay_within_the_document_scope(self):
        with self.assertRaisesRegex(ValidationError, 'outside the document scope'):
            EnrolmentDocument.model_validate({**DOCUMENT, 'institutions': ['Dječji vrtić Duga'],
                'excerpts': [{'content': 'Predškola.', 'institutions': ['Dječji vrtić Bajka']}]})

    def test_rejects_inverted_period_and_repeated_sources(self):
        with self.assertRaisesRegex(ValidationError, 'valid_until'):
            EnrolmentDocument.model_validate({**DOCUMENT, 'valid_until': '2026-05-10'})
        with self.assertRaisesRegex(ValidationError, 'own dataset_key'):
            EnrolmentSnapshot.model_validate({'snapshot_key': 's', 'verified_on': '2026-11-05',
                                              'documents': [DOCUMENT, DOCUMENT]})


class EnrolmentServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_imports_every_document_in_one_unit_of_work(self):
        snapshot = EnrolmentSnapshot.model_validate({'snapshot_key': 's', 'verified_on': '2026-11-05',
            'documents': [DOCUMENT, {**DOCUMENT, 'dataset_key': 'second'}]})
        work = SimpleNamespace(enrolment=SimpleNamespace(import_document=AsyncMock(return_value={'chunks': 2})))
        opened = []

        @asynccontextmanager
        async def uow():
            opened.append(True)
            yield work

        result = await EnrolmentDocumentService(snapshot, uow).import_data()
        self.assertEqual((len(opened), result['chunks']), (1, 4))
        self.assertEqual(EnrolmentDocumentService(snapshot).preview_import()['sources'][0]['excerpts'], 1)
        with self.assertRaisesRegex(RuntimeError, 'Unit of Work'):
            await EnrolmentDocumentService(snapshot).import_data()


if __name__ == '__main__':
    unittest.main()
