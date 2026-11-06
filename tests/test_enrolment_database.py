"""Rollback-only fixtures protect enrolment document scope, dates and revocation."""
import os
import unittest
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import urlparse

from KIDSic.dao.concrete.asyncpg_enrolment import AsyncpgEnrolmentDocumentRepository
from KIDSic.dao.concrete.asyncpg_kindergarten import AsyncpgKindergartenRepository
from KIDSic.dao.concrete.asyncpg_location import AsyncpgLocationRepository
from KIDSic.dao.concrete.asyncpg_source import AsyncpgSourceRepository
from KIDSic.db.database import database_pool
from KIDSic.dto.enrolment import EnrolmentDocument
from KIDSic.dto.rag import RagQuery
from KIDSic.dto.source import PlannedSource, SourceDefinition, SourceSnapshot
from KIDSic.exceptions import SourceImportError
from KIDSic.factories.rag import RagServiceFactory
from KIDSic.services.concrete.kindergarten_normalizer import normalize_records
from test_enrolment import CALL, DOCUMENT
from KIDSic.dto.location import LocationQuery
from test_sources import MUNICIPAL, source_client


@unittest.skipUnless(os.getenv('KIDSIC_TEST_DATABASE_URL'), 'Set KIDSIC_TEST_DATABASE_URL')
class EnrolmentDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        dsn = os.environ['KIDSIC_TEST_DATABASE_URL']
        if not urlparse(dsn).path.removeprefix('/').startswith('kidsic_test_'):
            raise ValueError('Use kidsic_test_* database')
        self.context = database_pool(dsn)
        self.pool = await self.context.__aenter__()
        self.c = await self.pool.acquire()
        self.tx = self.c.transaction(); await self.tx.start()
        client = source_client('municipal')
        definition = SourceDefinition('directory', 'https://example.invalid', 'directory', 'municipal')
        package = client.get_package.return_value
        rows = normalize_records([MUNICIPAL, {**MUNICIPAL, 'Id': 2, 'Naziv': 'DV Primjer-PO Druga',
                                'Adresa': 'Druga 2', 'TipVrtica': 'Područni'}], 'municipal')
        await AsyncpgSourceRepository(self.c).import_snapshot(SourceSnapshot(
            PlannedSource(definition, package, package.resources[0]), rows, datetime.now(timezone.utc)))
        self.enrolment = AsyncpgEnrolmentDocumentRepository(self.c)

        @asynccontextmanager
        async def work():
            yield SimpleNamespace(locations=AsyncpgLocationRepository(self.c), search=AsyncpgKindergartenRepository(self.c))
        self.rag = RagServiceFactory().create(work)
        self.query = RagQuery(city='Zagreb', name='Primjer', topics=['document'])

    async def asyncTearDown(self):
        await self.tx.rollback(); await self.pool.release(self.c)
        await self.context.__aexit__(None, None, None)

    async def load(self, **changes):
        document = EnrolmentDocument.model_validate({**DOCUMENT, **changes})
        return await self.enrolment.import_document(document, 'test-snapshot', datetime.now(timezone.utc))

    async def add_owner(self, name, provider='municipal'):
        owner = await self.c.fetchval('INSERT INTO kindergarten(name,provider_kind) VALUES ($1,$2) RETURNING id', name, provider)
        location = await self.c.fetchval("INSERT INTO location(kindergarten_id,name,settlement,settlement_key,municipality_id) VALUES ($1,$2,'Zagreb','zagreb',(SELECT id FROM municipality WHERE key='zagreb')) RETURNING id", owner, name)
        await self.c.execute("INSERT INTO source_record(source_id,batch_id,source_key,raw_data,kindergarten_id,location_id,match_status,match_method) SELECT id,active_batch_id,$1,'{}',$2,$3,'accepted','manual' FROM data_source WHERE dataset_key='directory'", str(owner), owner, location)
        return owner, location

    async def test_shared_rule_excludes_private_providers_and_includes_later_municipal_owners(self):
        await self.add_owner('Privatni primjer', 'private')
        await self.load(calls=[CALL])
        source_records = await self.c.fetchval("SELECT count(*) FROM source_record r JOIN data_source s ON s.id=r.source_id WHERE s.dataset_key='example-enrolment'")
        self.assertEqual(source_records, 1)
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM enrolment'), 1)
        owner, location = await self.add_owner('Kasniji gradski vrtić')
        rows = await AsyncpgLocationRepository(self.c).list_locations(LocationQuery(city='Zagreb'))
        private = next(r for r in rows if r['provider_kind'] == 'private')
        later = next(r for r in rows if r['kindergarten_id'] == owner)
        self.assertEqual(private['enrolment'], [])
        self.assertEqual(len(later['enrolment']), 1)
        later_context = await self.rag.retrieve(RagQuery(city='Zagreb',name='Kasniji',topics=['document']))
        self.assertEqual((later_context.status, later_context.evidence[0].scope), ('ok','municipality'))
        self.assertEqual(later_context.evidence[0].applies_to, [str(location)])
        self.assertEqual((await self.rag.retrieve(RagQuery(city='Zagreb',name='Privatni',topics=['document']))).status, 'no_evidence')

    async def test_named_document_never_reaches_another_municipal_owner(self):
        await self.add_owner('Drugi gradski vrtić')
        await self.load(institutions=['Dječji vrtić Primjer'],calls=[CALL])
        other = await self.rag.retrieve(RagQuery(city='Zagreb',name='Drugi',topics=['document']))
        self.assertEqual(other.status, 'no_evidence')
        rows = await AsyncpgLocationRepository(self.c).list_locations(LocationQuery(city='Zagreb',q='Drugi'))
        self.assertEqual(rows[0]['enrolment'], [])

    async def test_ownerless_accepted_evidence_requires_a_scope_at_commit(self):
        import asyncpg
        with self.assertRaises(asyncpg.CheckViolationError):
            async with self.c.transaction():
                await self.c.execute("INSERT INTO source_record(source_id,batch_id,source_key,raw_data,match_status,match_method) SELECT id,active_batch_id,'unscoped','{}','accepted','manual' FROM data_source WHERE dataset_key='directory'")
                await self.c.execute('SET CONSTRAINTS ALL IMMEDIATE')

    async def test_municipal_and_named_excerpts_reach_every_object_with_dates_and_licence(self):
        result = await self.load(valid_until=(date.today() + timedelta(days=30)).isoformat(), excerpts=[
            {'content': 'Zahtjevi se podnose od 13. svibnja 2026. do 22. svibnja 2026.'},
            {'content': 'Ovaj vrtić ne provodi upise.', 'institutions': ['Dječji vrtić Primjer']}])
        self.assertEqual((result['institutions'], result['records'], result['chunks']), (1, 2, 2))
        context = await self.rag.retrieve(self.query)
        self.assertEqual((context.status, context.total_matches), ('ok', 2))
        by_scope = {e.scope: e for e in context.evidence}
        self.assertEqual(set(by_scope), {'municipality', 'institution'})
        for item in context.evidence:
            self.assertEqual(len(item.applies_to), 2)  # institution-wide, not one object's
            self.assertEqual((item.reference_date, item.date_kind, item.temporal_status),
                             (date(2026, 5, 11), 'published', 'current'))
            self.assertEqual(item.sources[0].url, 'https://example.invalid/upis.pdf')
            self.assertEqual(item.sources[0].license, 'Ponovna uporaba uz navođenje izvora')
        self.assertIsNone(await self.c.fetchval(
            "SELECT observed_on FROM data_source WHERE dataset_key='example-enrolment'"))

    async def test_rounds_reach_every_object_of_the_institution_with_source_dates(self):
        result = await self.load(calls=[CALL, {**CALL, 'round': 'rolling', 'opens_at': None,
                                               'closes_at': '2999-08-31T23:59:59+02:00'}])
        self.assertEqual(result['enrolment_rounds'], 2)
        rows = await AsyncpgLocationRepository(self.c).list_locations(LocationQuery(city='Zagreb', q='Primjer'))
        self.assertEqual(len(rows), 2)
        for row in rows:
            rounds = {r['round']: r for r in row['enrolment']}
            self.assertEqual(set(rounds), {'main', 'rolling'})
            self.assertEqual((rounds['main']['application_url'], rounds['main']['channel'], rounds['main']['accepting']),
                             ('https://upis.example.invalid/', 'city_system', True))
            self.assertEqual((rounds['main']['reference_date'], rounds['main']['date_kind']), ('2026-05-11', 'published'))
            self.assertEqual(rounds['main']['source_url'], 'https://example.invalid/upis.pdf')
        await self.c.execute("UPDATE data_source SET import_allowed=false WHERE dataset_key='example-enrolment'")
        rows = await AsyncpgLocationRepository(self.c).list_locations(LocationQuery(city='Zagreb', q='Primjer'))
        self.assertEqual([r['enrolment'] for r in rows], [[], []])

    async def test_reimport_keeps_only_the_active_rounds_and_records_refusals(self):
        await self.load(calls=[CALL])
        await self.load(calls=[{**CALL, 'not_accepting': ['Dječji vrtić Primjer']}])
        [row, _] = await AsyncpgLocationRepository(self.c).list_locations(LocationQuery(city='Zagreb', q='Primjer'))
        self.assertEqual([r['accepting'] for r in row['enrolment']], [False])
        with self.assertRaisesRegex(SourceImportError, '0 active institutions'):
            await self.load(calls=[{**CALL, 'not_accepting': ['Dječji vrtić Nepostojeći']}])

    async def test_expired_period_is_historical_and_observed_date_is_kept(self):
        await self.load(reference_date='2020-05-11', date_kind='observed', valid_until='2021-08-31')
        [item] = (await self.rag.retrieve(self.query)).evidence
        self.assertEqual((item.reference_date, item.date_kind, item.temporal_status),
                         (date(2020, 5, 11), 'observed', 'historical'))
        self.assertEqual(await self.c.fetchval(
            "SELECT observed_on FROM data_source WHERE dataset_key='example-enrolment'"), date(2020, 5, 11))

    async def test_reimport_replaces_the_batch_and_revocation_hides_documents(self):
        await self.load()
        record = await self.c.fetchval("SELECT r.id FROM source_record r JOIN data_source s ON s.id=r.source_id WHERE s.dataset_key='example-enrolment'")
        await self.load(excerpts=[{'content': 'Nova verzija obavijesti.'}])
        self.assertEqual(await self.c.fetchval("SELECT r.id FROM source_record r JOIN data_source s ON s.id=r.source_id WHERE s.dataset_key='example-enrolment'"), record)
        [item] = (await self.rag.retrieve(self.query)).evidence
        self.assertEqual(item.content, 'Nova verzija obavijesti.')
        await self.c.execute("UPDATE data_source SET import_allowed=false WHERE dataset_key='example-enrolment'")
        self.assertEqual((await self.rag.retrieve(self.query)).status, 'no_evidence')
        with self.assertRaisesRegex(SourceImportError, 'disabled'):
            await self.load()

    async def test_unresolved_names_and_other_provider_kinds_are_rejected(self):
        with self.assertRaisesRegex(SourceImportError, '0 active institutions'):
            await self.load(excerpts=[{'content': 'Upis.', 'institutions': ['Dječji vrtić Nepostojeći']}])
        with self.assertRaisesRegex(SourceImportError, 'No active institutions'):
            await self.load(provider_kinds=['private'])
        with self.assertRaisesRegex(SourceImportError, 'No active institutions'):
            await self.load(municipality='rijeka')

    async def test_enrolment_records_never_keep_a_dropped_kindergarten_active(self):
        # A Zagreb seat makes the owner eligible through any accepted active record.
        await self.c.execute("INSERT INTO kindergarten_seat(kindergarten_id,municipality_id) SELECT id,(SELECT id FROM municipality WHERE key='zagreb') FROM kindergarten ON CONFLICT(kindergarten_id) DO UPDATE SET municipality_id=EXCLUDED.municipality_id")
        await self.load()
        await self.c.execute("UPDATE data_source SET import_allowed=false WHERE dataset_key='directory'")
        with self.assertRaisesRegex(SourceImportError, 'No active institutions'):
            await self.load()
        self.assertEqual((await self.rag.retrieve(self.query)).status, 'not_found')


if __name__ == '__main__':
    unittest.main()
