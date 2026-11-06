"""Synthetic database fixtures verify document scope and transaction cleanup."""
import os
import unittest
from urllib.parse import urlparse
from uuid import uuid4

import asyncpg
from KIDSic.db.database import database_pool
from KIDSic.db.uow.asyncpg import AsyncpgUnitOfWork
from KIDSic.dao.concrete.asyncpg_kindergarten import AsyncpgKindergartenRepository
from KIDSic.exceptions import PersistenceError


@unittest.skipUnless(os.getenv('KIDSIC_TEST_DATABASE_URL'), 'Set KIDSIC_TEST_DATABASE_URL')
class SearchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        dsn = os.environ['KIDSIC_TEST_DATABASE_URL']
        if not urlparse(dsn).path.removeprefix('/').startswith('kidsic_test_'):
            raise ValueError('Use kidsic_test_* database')
        self.ctx = database_pool(dsn)
        self.pool = await self.ctx.__aenter__()
        self.c = await self.pool.acquire()
        self.tx = self.c.transaction()
        await self.tx.start()
        self.repo = AsyncpgKindergartenRepository(self.c)
        self.batch = uuid4()
        self.source = await self.c.fetchval("INSERT INTO data_source(dataset_key,title,publisher,url,import_allowed,active_batch_id) VALUES ('directory','Directory','Test','https://example.invalid',true,$1) RETURNING id", self.batch)

    async def asyncTearDown(self):
        await self.tx.rollback()
        await self.pool.release(self.c)
        await self.ctx.__aexit__(None,None,None)

    async def record(self, owner, location=None):
        return await self.c.fetchval("INSERT INTO source_record(source_id,batch_id,source_key,raw_data,kindergarten_id,location_id,match_status,match_method) VALUES ($1,$2,$3,'{}',$4,$5,'accepted','manual') RETURNING id",self.source,self.batch,str(uuid4()),owner,location)

    async def chunk(self, owner, location, record, content='Sourced document'):
        await self.c.execute("INSERT INTO knowledge_chunk(kindergarten_id,location_id,source_record_id,ordinal,content,source_url) VALUES ($1,$2,$3,0,$4,'https://example.invalid/evidence')",owner,location,record,content)

    async def test_context_respects_owner_facility_and_institution_scope(self):
        owner = await self.c.fetchval("INSERT INTO kindergarten(name) VALUES ('Selected') RETURNING id")
        other = await self.c.fetchval("INSERT INTO kindergarten(name) VALUES ('Other') RETURNING id")
        async def location(k):
            return await self.c.fetchval("INSERT INTO location(kindergarten_id,name,settlement,settlement_key) VALUES ($1,'Branch','Zagreb','zagreb') RETURNING id", k)
        selected, sibling, elsewhere = await location(owner), await location(owner), await location(other)
        for k,l in ((owner,selected),(owner,sibling),(other,elsewhere),(owner,None)):
            await self.chunk(k,l,await self.record(k,l))
        rows = await self.repo.retrieve_context(location_ids=[selected])
        self.assertEqual({r['location_id'] for r in rows},{selected,None})
        self.assertEqual({r['kindergarten_id'] for r in rows},{owner})
        self.assertTrue(all(r['source_url'] for r in rows))
        rows = await self.repo.retrieve_context(location_ids=[],kindergarten_ids=[owner])
        self.assertEqual([r['location_id'] for r in rows],[None])
        await self.c.execute('UPDATE data_source SET import_allowed=false WHERE id=$1',self.source)
        self.assertEqual(await self.repo.retrieve_context(location_ids=[selected]),[])

    async def test_context_rejects_cross_owner_chunks_and_invalid_limits(self):
        owner = await self.c.fetchval("INSERT INTO kindergarten(name) VALUES ('Owner') RETURNING id")
        other = await self.c.fetchval("INSERT INTO kindergarten(name) VALUES ('Other') RETURNING id")
        record = await self.record(owner)
        await self.chunk(other,None,record)
        self.assertEqual(await self.repo.retrieve_context(location_ids=[],kindergarten_ids=[other]),[])
        for value in (0,31,None,True):
            with self.assertRaises(ValueError):
                await self.repo.retrieve_context(location_ids=[],limit=value)

    async def test_driver_errors_cross_the_read_transaction_as_persistence_errors(self):
        before = self.pool.get_size() - self.pool.get_idle_size()
        with self.assertRaises(PersistenceError) as error:
            async with AsyncpgUnitOfWork(self.pool) as work:
                await work.search.retrieve_context(location_ids=['not-a-uuid'])
        self.assertIsInstance(error.exception.__cause__, asyncpg.PostgresError)
        self.assertEqual(self.pool.get_size() - self.pool.get_idle_size(), before)

    async def test_unit_of_work_releases_connection_after_error(self):
        before=self.pool.get_size()-self.pool.get_idle_size()
        with self.assertRaisesRegex(RuntimeError,'synthetic failure'):
            async with AsyncpgUnitOfWork(self.pool) as uow:
                await uow.search.retrieve_context(location_ids=[])
                raise RuntimeError('synthetic failure')
        self.assertEqual(self.pool.get_size()-self.pool.get_idle_size(),before)
        async with AsyncpgUnitOfWork(self.pool) as uow:
            self.assertIsInstance(await uow.search.retrieve_context(location_ids=[]),list)
