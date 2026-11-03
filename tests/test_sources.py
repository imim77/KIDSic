"""Source planning and mapping use synthetic rows shaped like the live JSONs."""
import copy
import json
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from KIDSic.commands.register_sources import SourceRegistrationCommand
from KIDSic.config.settings import Settings
from KIDSic.dto.ckan import CkanPackage
from KIDSic.dto.source import SourceDefinition, name_key
from KIDSic.exceptions import SourceImportError
from KIDSic.services.concrete.kindergarten_normalizer import normalize_records
from KIDSic.services.concrete.source import SourceService


NATIONAL = {'Naziv': 'Dječji vrtić "Primjer"', 'Adresa': 'Primjer 1', 'Mjesto': 'Varaždin',
            'ePosta': '', 'Telefon': '', 'Zupanija': 'Varaždinska županija ', 'PostanskiBroj': '42000'}
MUNICIPAL = {'Id': 1, 'Naziv': 'DV Primjer-matični objekt', 'Adresa': 'Primjer 1',
             'X': '15,9452', 'Y': '45.8017', 'Web': None, 'Email': 'test@example.invalid',
             'Telefon': '', 'TipVrtica': 'Matični', 'VrstaVrtica': 'Gradski DV',
             'GradskaCetvrt': 'Trešnjevka-Sjever'}


def source_client(name='national'):
    payload = json.loads((Path(__file__).parent / f'fixtures/ckan_{name}.json').read_text())
    return SimpleNamespace(get_package=AsyncMock(return_value=CkanPackage.model_validate(payload['result'])),
                           download_records=AsyncMock(return_value=[copy.deepcopy(NATIONAL)]))


class NormalizationTests(unittest.TestCase):
    def test_national_identity_is_independent_of_contacts_and_diacritics(self):
        first = normalize_records([NATIONAL], 'national')[0]
        second = normalize_records([{**NATIONAL, 'Telefon': '123', 'Mjesto': 'Varazdin'}], 'national')[0]
        self.assertEqual(first.source_key, second.source_key)
        self.assertIsNone(first.email)
        self.assertEqual(first.postal_code, '42000')
        self.assertEqual(name_key(first.name), name_key('DV Primjer'))

    def test_national_rows_are_institution_seats_with_confirmed_municipality(self):
        row = normalize_records([NATIONAL], 'national')[0]
        self.assertEqual((row.scope, row.settlement, row.municipality), ('institution', 'Varaždin', 'varazdin'))
        sesvete = normalize_records([{**NATIONAL, 'Mjesto': 'Sesvete', 'Zupanija': 'Grad Zagreb'}], 'national')[0]
        self.assertEqual(sesvete.municipality, 'zagreb')
        # A curated name in another county is not assumed to be the same municipality.
        self.assertIsNone(normalize_records([{**NATIONAL, 'Zupanija': 'Druga županija'}], 'national')[0].municipality)

    def test_explicitly_removed_varazdin_associations_are_not_reimported(self):
        names = ('udruga DRUŠTVO NAŠA DJECA',
                 'Udruga Društvo športske rekreacije "SPORTSKA ABECEDA"',
                 'udruga Univerzalna športska škola "Junior"')
        rows = normalize_records([NATIONAL, *({**NATIONAL, 'Naziv': name} for name in names)], 'national')
        self.assertEqual([row.name for row in rows], [NATIONAL['Naziv']])
        self.assertEqual(normalize_records([{**NATIONAL, 'Naziv': names[0]}], 'national'), ())
        # The exclusion is scoped to the requested institutions in Varaždin.
        self.assertEqual(len(normalize_records([{**NATIONAL, 'Naziv': names[0], 'Mjesto': 'Zagreb'}], 'national')), 1)
        self.assertEqual(len(normalize_records([{**NATIONAL, 'Naziv': 'Dječji vrtić Junior'}], 'national')), 1)

    def test_zagreb_address_suffix_becomes_settlement(self):
        row = normalize_records([{**MUNICIPAL, 'Adresa': 'Augusta Šenoe 26A, Đurđekovec'}], 'municipal')[0]
        self.assertEqual((row.address, row.settlement, row.municipality, row.scope),
                         ('Augusta Šenoe 26A', 'Đurđekovec', 'zagreb', 'location'))
        plain = normalize_records([{**MUNICIPAL, 'Adresa': 'Remetski kamenjak 1 C,'}], 'municipal')[0]
        self.assertEqual((plain.address, plain.settlement), ('Remetski kamenjak 1 C,', 'Zagreb'))

    def test_zagreb_objects_keep_parent_name_and_decimal_comma_coordinates(self):
        rows = normalize_records([MUNICIPAL, {**MUNICIPAL, 'Id': 2, 'Naziv': 'DV Primjer-PO Druga',
                                              'TipVrtica': 'Područni'}], 'municipal')
        self.assertEqual(rows[0].name, rows[1].name)
        self.assertEqual(rows[1].kind, 'branch')
        self.assertEqual(rows[0].longitude, 15.9452)
        self.assertEqual(rows[0].provider_kind, 'municipal')
        self.assertEqual(normalize_records([{**MUNICIPAL, 'VrstaVrtica': 'Obrt za čuvanje djece'}],
                                           'other')[0].provider_kind, 'childminder')

    def test_empty_invalid_and_duplicate_rows_fail_instead_of_clearing_data(self):
        bad = [[], [{**NATIONAL, 'Naziv': ''}], [NATIONAL, NATIONAL],
               [{**NATIONAL, 'PostanskiBroj': 42000}]]
        for records in bad:
            with self.assertRaises(SourceImportError):
                normalize_records(records, 'national')
        for changes in ({'X': 'invalid'}, {'X': None}, {'X': '45.8', 'Y': '15.9'},
                        {'X': 'nan'}, {'VrstaVrtica': 'Unexpected'}):
            with self.assertRaises(SourceImportError):
                normalize_records([{**MUNICIPAL, **changes}], 'municipal')


class SourceServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.definition = SourceDefinition('national', 'https://data.gov.hr/ckan', 'djecji-vrtici', 'national')
        self.client = source_client()

    async def test_dry_run_downloads_without_a_uow_and_registration_does_not_download(self):
        service = SourceService({'national': self.client}, [self.definition])
        self.assertEqual(len((await service.preview_sources())['sources']), 1)
        self.client.download_records.assert_not_awaited()
        self.assertEqual((await service.preview_import())['sources'][0]['records'], 1)
        with self.assertRaises(RuntimeError):
            await service.register_sources()

    async def test_invalid_later_source_never_opens_transaction(self):
        second = SourceDefinition('second', 'https://example.invalid', 'missing', 'national')
        other = source_client()
        other.get_package.side_effect = SourceImportError('missing resource')
        opened = []

        @asynccontextmanager
        async def work():
            opened.append(True)
            yield SimpleNamespace(sources=SimpleNamespace(register=AsyncMock()))

        service = SourceService({'national': self.client, 'second': other}, [self.definition, second], work)
        with self.assertRaises(SourceImportError):
            await service.register_sources()
        with self.assertRaises(SourceImportError):
            await service.import_data()
        self.assertEqual(opened, [])

    async def test_ambiguous_missing_or_unlicensed_resources_are_rejected(self):
        package = self.client.get_package.return_value
        for resources, license_id in (([], 'open-license'), (package.resources * 2, 'open-license'),
                                       (package.resources, None)):
            self.client.get_package.return_value = package.model_copy(update={
                'resources': resources, 'license_id': license_id})
            with self.assertRaises(SourceImportError):
                await SourceService({'national': self.client}, [self.definition]).preview_sources()

    async def test_cli_dry_run_needs_no_database_environment_or_pool(self):
        @asynccontextmanager
        async def fake_http(*args, **kwargs):
            yield SimpleNamespace()

        service = SourceService({'national': self.client}, [self.definition])
        with patch.dict('os.environ', {}, clear=True), patch(
            'KIDSic.services.dependency.database_pool', side_effect=AssertionError('database opened')
        ), patch('KIDSic.services.dependency.httpx.AsyncClient', fake_http), patch(
            'KIDSic.services.dependency.SourceServiceFactory.create', return_value=service
        ):
            result = await SourceRegistrationCommand(Settings.from_env(require_database=False)).run(True)
        self.assertTrue(result['dry_run'])
