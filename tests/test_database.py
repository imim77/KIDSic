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
from KIDSic.exceptions import PersistenceError
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
        self.municipalities={key:await self.c.fetchval("INSERT INTO municipality(key,name,aliases) VALUES ($1,$2,$3) ON CONFLICT (key) DO UPDATE SET aliases=EXCLUDED.aliases RETURNING id",key,name,[alias]) for key,name,alias in (('varazdin','Varaždin','varazdina'),('zagreb','Zagreb','zagreba'))}
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
        l=await self.c.fetchval("INSERT INTO location(kindergarten_id,name,settlement,settlement_key,municipality_id) VALUES ($1,$2,$3,$4,$5) RETURNING id",k,name,city,key,self.municipalities[key])
        r=await self.c.fetchval("INSERT INTO source_record(source_id,batch_id,raw_data,kindergarten_id,location_id,match_status,match_method) VALUES ($1,$2,$3,$4,$5,'accepted','new') RETURNING id",self.source,self.batch,{'synthetic':True},k,l)
        if minimum is not None:
            await self.c.execute('INSERT INTO program(kindergarten_id,location_id,source_record_id,name,min_age_months,max_age_months_exclusive,verified_on) VALUES ($1,$2,$3,$4,$5,$6,$7)',k,l,r,'Synthetic nursery',minimum,maximum,date(2026,10,1))
        return k,l,r

    async def chunk(self, fixture, text):
        k, l, r = fixture
        return await self.c.fetchval("INSERT INTO knowledge_chunk(kindergarten_id,location_id,source_record_id,ordinal,content,source_url,content_sha256) VALUES ($1,$2,$3,0,$4,'https://example.invalid/evidence',$5) RETURNING id", k,l,r,text,'a'*64)

    async def test_croatian_question_filters_city_and_24_months(self):
        result=await self.service.recommend('Imam dijete od 2 godine i iz varazdina sam koji su mi vrtici opcija',as_of=date(2026,11,1))
        self.assertEqual(result['criteria'],{'city':'varazdin','age_months':24})
        self.assertEqual([r['name'] for r in result['confirmed']],['Eligible'])
        self.assertTrue(result['confirmed'][0]['age_evidence'][0]['source_url'])
        self.assertEqual([r['name'] for r in result['age_unknown']],['Unknown age'])
        with self.assertRaises(ValueError):
            await parse_request(self.repo,'Dijete od 2 godine iz Zagreba ili Varazdina')

    async def test_area_filters_candidates_before_rag_retrieval(self):
        await self.c.execute("UPDATE location SET attributes=$2 WHERE id=$1", self.eligible[1],
                             {'quarter': 'Široke ledine', 'suburb': 'Banfica'})
        await self.c.execute("UPDATE location SET attributes=$2 WHERE id=$1", self.old[1],
                             {'quarter': 'Đurek', 'suburb': 'Centar'})
        await self.chunk(self.eligible, 'Dijete od 2 godine iz Varaždina na Banfici')
        await self.chunk(self.other, 'Dijete od 2 godine iz Varaždina na Banfici drugi grad')
        result = await self.service.recommend('Dijete od 2 godine iz Varaždina na Banfici',
            as_of=date(2026, 11, 1))
        self.assertEqual(result['criteria']['area'], 'Banfica')
        self.assertEqual([row['location_id'] for row in result['confirmed']], [self.eligible[1]])
        self.assertEqual(result['confirmed'][0]['quarter'], 'Široke ledine')
        self.assertEqual(result['age_unknown'], [])
        self.assertEqual([row['location_id'] for row in result['context']], [self.eligible[1]])
        rows = await self.repo.find_options(city='varazdin', age_months=24,
                                           area='Široke ledine', include_unknown=True)
        self.assertEqual([row['location_id'] for row in rows], [self.eligible[1]])
        self.assertEqual(await self.repo.find_options(city='varazdin', age_months=24,
                                                     area='Nepostojeći kvart', include_unknown=True), [])
        with self.assertRaisesRegex(ValueError, 'jedan kvart'):
            await parse_request(self.repo, 'Dijete od 2 godine iz Varaždina, Banfica ili Centar')
        # A facility can stay active while the separate geographic source is disabled.
        geo_source = await self.c.fetchval("INSERT INTO data_source(dataset_key,title,publisher,url,import_allowed,active_batch_id) VALUES ('geo','Geo','Test','https://example.invalid/geo',false,$1) RETURNING id", self.batch)
        geo_record = await self.c.fetchval("INSERT INTO source_record(source_id,batch_id,raw_data,kindergarten_id,location_id,match_status,match_method) VALUES ($1,$2,'{}',$3,$4,'accepted','manual') RETURNING id", geo_source, self.batch, self.eligible[0], self.eligible[1])
        await self.c.execute('UPDATE location SET provenance=$2 WHERE id=$1', self.eligible[1],
                             {field: {'source_record_id': str(geo_record)} for field in ('quarter', 'suburb')})
        self.assertNotIn('Banfica', [row['name'] for row in await self.repo.list_areas(city='varazdin')])
        self.assertEqual(await self.repo.find_options(city='varazdin', age_months=24,
                                                     area='Banfica', include_unknown=True), [])
        # Inactive snapshots must not contribute area names to the parser.
        await self.c.execute('UPDATE data_source SET import_allowed=false WHERE id=$1', self.source)
        self.assertEqual(await self.repo.list_areas(city='varazdin'), [])

    async def test_boundary_staleness_and_unapproved_sources(self):
        rows=await self.repo.find_options(city='Varaždin',age_months=36,as_of=date(2026,11,1))
        self.assertEqual([r['name'] for r in rows],['Older children'])
        await self.c.execute('UPDATE data_source SET stale_after_days=7 WHERE id=$1',self.source)
        self.assertEqual(await self.repo.find_options(city='varazdin',age_months=24,as_of=date(2026,11,1)),[])
        await self.c.execute('UPDATE data_source SET import_allowed=false WHERE id=$1',self.source)
        self.assertEqual(await self.repo.find_options(city='varazdin',age_months=24,include_unknown=True),[])

    async def test_rag_never_introduces_other_city_or_age_group(self):
        await self.chunk(self.eligible, 'Dijete od 2 godine iz Varazdina upute')
        await self.chunk(self.other, 'Dijete od 2 godine iz Varazdina drugi grad')
        await self.chunk(self.old, 'Dijete od 2 godine iz Varazdina starija djeca')
        k,l,r=self.eligible
        older_program=await self.c.fetchval("INSERT INTO program(kindergarten_id,location_id,source_record_id,name,min_age_months,max_age_months_exclusive,verified_on) VALUES ($1,$2,$3,'Older group same location',36,84,'2026-10-01') RETURNING id",k,l,r)
        await self.c.execute("INSERT INTO knowledge_chunk(kindergarten_id,location_id,program_id,source_record_id,ordinal,content,source_url,content_sha256) VALUES ($1,$2,$3,$4,1,'Dijete od 2 godine iz Varazdina wrong age same location','https://example.invalid/older',$5)",k,l,older_program,r,'a'*64)
        result=await self.service.recommend('Dijete od 2 godine iz Varazdina',as_of=date(2026,11,1))
        self.assertEqual(len(result['context']),1)
        self.assertEqual(result['context'][0]['kindergarten_id'],self.eligible[0])
        self.assertIn('source_url',result['context'][0])

    async def test_failed_batch_preserves_active_data_and_new_snapshot_removes_it(self):
        k,l,_=self.eligible
        await self.c.execute("INSERT INTO source_record(source_id,batch_id,raw_data,kindergarten_id,location_id,match_status) VALUES ($1,$2,$3,$4,$5,'candidate')",self.source,uuid.uuid4(),{'failed':True},k,l)
        self.assertEqual(len(await self.repo.find_options(city='varazdin',age_months=24,as_of=date(2026,11,1))),1)
        await self.c.execute('UPDATE data_source SET active_batch_id=$2 WHERE id=$1',self.source,uuid.uuid4())
        self.assertEqual(await self.repo.find_options(city='varazdin',age_months=24,as_of=date(2026,11,1)),[])

    async def test_two_datasets_contribute_to_same_kindergarten(self):
        k,l,_=self.eligible
        second=await self.c.fetchval("INSERT INTO data_source(dataset_key,title,publisher,url,import_allowed,active_batch_id) VALUES ('city','City','City','https://example.invalid/city',true,$1) RETURNING id",self.batch)
        await self.c.execute("INSERT INTO source_record(source_id,batch_id,raw_data,kindergarten_id,location_id,match_status,match_method) VALUES ($1,$2,$3,$4,$5,'accepted','new')",second,self.batch,{'city_attributes':'hall'},k,l)
        self.assertEqual(await self.c.fetchval('SELECT count(DISTINCT source_id) FROM source_record WHERE kindergarten_id=$1',k),2)
        self.assertEqual(len(await self.repo.find_options(city='varazdin',age_months=24,as_of=date(2026,11,1))),1)

    async def test_seat_stands_in_only_without_an_attested_object(self):
        k=await self.c.fetchval("INSERT INTO kindergarten(name,seat_address,seat_settlement,seat_settlement_key) VALUES ('Seat only','Sjedište 1','Varaždin','varazdin') RETURNING id")
        r=await self.c.fetchval("INSERT INTO source_record(source_id,batch_id,raw_data,kindergarten_id,match_status,match_method) VALUES ($1,$2,$3,$4,'accepted','new') RETURNING id",self.source,self.batch,{'synthetic':True},k)
        await self.c.execute("INSERT INTO program(kindergarten_id,source_record_id,name,min_age_months,max_age_months_exclusive,verified_on) VALUES ($1,$2,'Institution nursery',12,36,'2026-10-01')",k,r)
        await self.c.execute("INSERT INTO knowledge_chunk(kindergarten_id,source_record_id,ordinal,content,source_url,content_sha256) VALUES ($1,$2,0,'jaslice upute ustanove','https://example.invalid/seat',$3)",k,r,'b'*64)
        result=await self.service.recommend('Dijete od 2 godine iz Varazdina',as_of=date(2026,11,1))
        seat=[row for row in result['confirmed'] if row['name']=='Seat only']
        self.assertEqual([(row['scope'],row['location_id'],row['address']) for row in seat],[('seat',None,'Sjedište 1')])
        self.assertEqual(await self.repo.retrieve_context(location_ids=[],kindergarten_ids=[k],text='jaslice'),await self.repo.retrieve_context(location_ids=[],kindergarten_ids=[k],text='upute'))
        self.assertEqual(len(await self.repo.retrieve_context(location_ids=[],kindergarten_ids=[k],text='jaslice')),1)
        # An object without its own active record does not appear; once attested it replaces the seat.
        l=await self.c.fetchval("INSERT INTO location(kindergarten_id,name,settlement,settlement_key) VALUES ($1,'Old object','Varaždin','varazdin') RETURNING id",k)
        rows=await self.repo.find_options(city='varazdin',age_months=24,as_of=date(2026,11,1))
        self.assertEqual([row['scope'] for row in rows if row['kindergarten_id']==k],['seat'])
        await self.c.execute("INSERT INTO source_record(source_id,batch_id,raw_data,kindergarten_id,location_id,match_status,match_method) VALUES ($1,$2,$3,$4,$5,'accepted','name')",self.source,self.batch,{'synthetic':True},k,l)
        rows=await self.repo.find_options(city='varazdin',age_months=24,as_of=date(2026,11,1))
        self.assertEqual([(row['scope'],row['location_id']) for row in rows if row['kindergarten_id']==k],[('location',l)])

    async def test_municipality_search_includes_its_settlements(self):
        k=await self.c.fetchval("INSERT INTO kindergarten(name) VALUES ('Sesvete object') RETURNING id")
        l=await self.c.fetchval("INSERT INTO location(kindergarten_id,name,settlement,settlement_key,municipality_id) VALUES ($1,'Sesvete object','Sesvete','sesvete',$2) RETURNING id",k,self.municipalities['zagreb'])
        await self.c.execute("INSERT INTO source_record(source_id,batch_id,raw_data,kindergarten_id,location_id,match_status,match_method) VALUES ($1,$2,$3,$4,$5,'accepted','new')",self.source,self.batch,{'synthetic':True},k,l)
        for city in ('zagreba','sesvete'):
            rows=await self.repo.find_options(city=city,age_months=24,include_unknown=True)
            self.assertIn('Sesvete object',[row['name'] for row in rows])
        rows=await self.repo.find_options(city='sesvete',age_months=24,include_unknown=True)
        self.assertEqual([(row['settlement'],row['municipality']) for row in rows],[('Sesvete','Zagreb')])

    async def test_enrolment_scope_constraints(self):
        k,l,r=self.eligible
        bad=(("INSERT INTO enrolment(kindergarten_id,municipality_id,source_record_id,academic_year,application_url,channel) VALUES ($1,$2,$3,'2027./2028.','https://example.invalid','city_system')",(k,self.municipalities['zagreb'],r),asyncpg.CheckViolationError),
             ("INSERT INTO enrolment(kindergarten_id,source_record_id,academic_year,application_url) VALUES ($1,$2,'2027./2028.','https://example.invalid')",(k,r),asyncpg.NotNullViolationError))
        for sql,args,error in bad:
            with self.assertRaises(error):
                async with self.c.transaction():
                    await self.c.execute(sql,*args)
        await self.c.execute("INSERT INTO enrolment(municipality_id,source_record_id,academic_year,application_url,channel) VALUES ($1,$2,'2027./2028.','https://example.invalid','city_system')",self.municipalities['zagreb'],r)

    async def test_cross_owner_and_invalid_age_are_rejected(self):
        with self.assertRaises(asyncpg.ForeignKeyViolationError):
            async with self.c.transaction():
                await self.c.execute('INSERT INTO program(kindergarten_id,location_id,source_record_id,name,verified_on) VALUES ($1,$2,$3,\'bad\',CURRENT_DATE)',self.other[0],self.eligible[1],self.eligible[2])
        with self.assertRaises(ValueError):
            await self.repo.find_options(city='varazdin',age_months=-1)

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
                await uow.search.list_cities()
                raise RuntimeError('synthetic failure')
        self.assertEqual(self.pool.get_size()-self.pool.get_idle_size(),before)
        async with AsyncpgUnitOfWork(self.pool) as uow:
            self.assertIsInstance(await uow.search.list_cities(),list)
