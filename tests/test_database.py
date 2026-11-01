"""Synthetic integration fixtures: these are not real Varaždin kindergartens."""
import os
from pathlib import Path
import sys
import unittest
import uuid
from datetime import date
from urllib.parse import urlparse

import asyncpg
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from KIDSic.db.database import database_pool
from KIDSic.db.uow.asyncpg import AsyncpgUnitOfWork
from contextlib import asynccontextmanager
from types import SimpleNamespace
from KIDSic.dao.concrete.asyncpg_kindergarten import AsyncpgKindergartenRepository
from KIDSic.services.concrete.request_parser import parse_request
from KIDSic.factories.kindergarten_search import KindergartenSearchServiceFactory


@unittest.skipUnless(os.getenv('KIDSIC_TEST_DATABASE_URL'),'Set KIDSIC_TEST_DATABASE_URL')
class SearchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        dsn=os.environ['KIDSIC_TEST_DATABASE_URL']
        if not urlparse(dsn).path.removeprefix('/').startswith('kidsic_test_'):
            raise ValueError('Use kidsic_test_* database')
        self.ctx=database_pool(dsn)
        self.pool=await self.ctx.__aenter__()
        self.c=await self.pool.acquire()
        self.tx=self.c.transaction(); await self.tx.start()
        self.repo=AsyncpgKindergartenRepository(self.c)
        @asynccontextmanager
        async def uow():
            yield SimpleNamespace(search=self.repo)
        self.service=KindergartenSearchServiceFactory().create(uow)
        self.batch=uuid.uuid4()
        self.source=await self.c.fetchval("INSERT INTO data_source(dataset_key,title,publisher,url,import_allowed,active_batch_id) VALUES ('directory','Directory','Test','https://example.invalid',true,$1) RETURNING id", self.batch)
        self.eligible=await self.fixture('Eligible', 'Varaždin', 12,36)
        self.old=await self.fixture('Older children','Varaždin',36,84)
        self.other=await self.fixture('Other city','Zagreb',12,36)
        self.unknown=await self.fixture('Unknown age','Varaždin',None,None)

    async def asyncTearDown(self):
        await self.tx.rollback();await self.pool.release(self.c);await self.ctx.__aexit__(None,None,None)

    async def fixture(self,name,city,minimum,maximum):
        k=await self.c.fetchval('INSERT INTO kindergarten(name) VALUES ($1) RETURNING id',name)
        key={'Varaždin':'varazdin','Zagreb':'zagreb'}[city]
        l=await self.c.fetchval("INSERT INTO location(kindergarten_id,name,city,city_key,city_aliases) VALUES ($1,$2,$3,$4,$5) RETURNING id",k,name,city,key,['varazdina'] if key=='varazdin' else ['zagreba'])
        r=await self.c.fetchval("INSERT INTO source_record(source_id,batch_id,raw_data,kindergarten_id,location_id,match_status) VALUES ($1,$2,$3,$4,$5,'accepted') RETURNING id",self.source,self.batch,{'synthetic':True},k,l)
        if minimum is not None:
            await self.c.execute('INSERT INTO program(kindergarten_id,location_id,source_record_id,name,min_age_months,max_age_months_exclusive,verified_on) VALUES ($1,$2,$3,$4,$5,$6,$7)',k,l,r,'Synthetic nursery',minimum,maximum,date(2026,10,1))
        return k,l,r


    async def test_croatian_question_filters_city_and_24_months(self):
        result=await self.service.recommend('Imam dijete od 2 godine i iz varazdina sam koji su mi vrtici opcija',as_of=date(2026,11,1))
        self.assertEqual(result['criteria'],{'city':'varazdin','age_months':24})
        self.assertEqual([r['name'] for r in result['confirmed']],['Eligible'])
        self.assertTrue(result['confirmed'][0]['age_evidence'][0]['source_url'])
        self.assertEqual([r['name'] for r in result['age_unknown']],['Unknown age'])
        with self.assertRaises(ValueError):
            await parse_request(self.repo,'Dijete od 2 godine iz Zagreba ili Varazdina')

    async def test_boundary_staleness_and_unapproved_sources(self):
        rows=await self.repo.find_options(city='Varaždin',age_months=36,as_of=date(2026,11,1))
        self.assertEqual([r['name'] for r in rows],['Older children'])
        await self.c.execute('UPDATE data_source SET stale_after_days=7 WHERE id=$1',self.source)
        self.assertEqual(await self.repo.find_options(city='varazdin',age_months=24,as_of=date(2026,11,1)),[])
        await self.c.execute('UPDATE data_source SET import_allowed=false WHERE id=$1',self.source)
        self.assertEqual(await self.repo.find_options(city='varazdin',age_months=24,include_unknown=True),[])



    async def test_failed_batch_preserves_active_data_and_new_snapshot_removes_it(self):
        k,l,_=self.eligible
        await self.c.execute("INSERT INTO source_record(source_id,batch_id,raw_data,kindergarten_id,location_id,match_status) VALUES ($1,$2,$3,$4,$5,'candidate')",self.source,uuid.uuid4(),{'failed':True},k,l)
        self.assertEqual(len(await self.repo.find_options(city='varazdin',age_months=24,as_of=date(2026,11,1))),1)
        await self.c.execute('UPDATE data_source SET active_batch_id=$2 WHERE id=$1',self.source,uuid.uuid4())
        self.assertEqual(await self.repo.find_options(city='varazdin',age_months=24,as_of=date(2026,11,1)),[])

    async def test_two_datasets_contribute_to_same_kindergarten(self):
        k,l,_=self.eligible
        second=await self.c.fetchval("INSERT INTO data_source(dataset_key,title,publisher,url,import_allowed,active_batch_id) VALUES ('city','City','City','https://example.invalid/city',true,$1) RETURNING id",self.batch)
        await self.c.execute("INSERT INTO source_record(source_id,batch_id,raw_data,kindergarten_id,location_id,match_status) VALUES ($1,$2,$3,$4,$5,'accepted')",second,self.batch,{'city_attributes':'hall'},k,l)
        self.assertEqual(await self.c.fetchval('SELECT count(DISTINCT source_id) FROM source_record WHERE kindergarten_id=$1',k),2)
        self.assertEqual(len(await self.repo.find_options(city='varazdin',age_months=24,as_of=date(2026,11,1))),1)

    async def test_cross_owner_and_invalid_age_are_rejected(self):
        with self.assertRaises(asyncpg.ForeignKeyViolationError):
            async with self.c.transaction():
                await self.c.execute('INSERT INTO program(kindergarten_id,location_id,source_record_id,name,verified_on) VALUES ($1,$2,$3,\'bad\',CURRENT_DATE)',self.other[0],self.eligible[1],self.eligible[2])
        with self.assertRaises(ValueError):
            await self.repo.find_options(city='varazdin',age_months=-1)
