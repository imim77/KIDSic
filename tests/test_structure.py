"""Infrastructure and service wiring checks independent of external sources."""
from contextlib import asynccontextmanager
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

from KIDSic.config.settings import Settings
from KIDSic.factories.kindergarten_search import KindergartenSearchServiceFactory


class ServiceWiringTests(unittest.IsolatedAsyncioTestCase):
    async def test_service_shares_one_uow_and_preserves_candidate_scope(self):
        repository = SimpleNamespace(
            list_cities=AsyncMock(return_value=[{'city_key':'varazdin','city_aliases':['varazdina']}]),
            find_options=AsyncMock(return_value=[
                {'location_id':'location-1','kindergarten_id':'k-1','age_status':'confirmed','age_evidence':[{'program_id':'program-1'}]},
                {'location_id':None,'kindergarten_id':'seat-only','age_status':'confirmed','age_evidence':[{'program_id':'program-2'}]},
                {'location_id':'unknown','age_status':'unknown','age_evidence':[]},
            ]),
            retrieve_context=AsyncMock(return_value=[{'source_url':'https://example.invalid'}]),
        )
        events=[]
        @asynccontextmanager
        async def uow_factory():
            events.append('enter')
            try:
                yield SimpleNamespace(search=repository)
            finally:
                events.append('exit')
        service=KindergartenSearchServiceFactory().create(uow_factory)
        result=await service.recommend('Dijete od 2 godine iz Varazdina')
        self.assertEqual(events,['enter','exit'])
        self.assertEqual(result['criteria'],{'city':'varazdin','age_months':24})
        repository.find_options.assert_awaited_once_with(city='varazdin',age_months=24,as_of=None,include_unknown=True)
        self.assertEqual(repository.retrieve_context.await_args.kwargs['location_ids'],['location-1'])
        self.assertEqual(repository.retrieve_context.await_args.kwargs['kindergarten_ids'],['seat-only'])
        self.assertEqual(repository.retrieve_context.await_args.kwargs['program_ids'],['program-1','program-2'])
        self.assertEqual(len(result['age_unknown']),1)

    def test_settings_reject_invalid_pool_and_non_postgres_urls(self):
        for values in ({'database_url':'sqlite://'}, {'database_url':'postgresql://host/db','pool_min_size':5,'pool_max_size':1}):
            with self.assertRaises(ValueError):
                Settings(**values)
