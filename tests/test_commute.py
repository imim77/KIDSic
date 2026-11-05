"""Commute tests cover full-catalogue ranking and clarification before routing."""
import asyncio
from contextlib import closing
from datetime import timedelta
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

from KIDSic.api.commute_tools import CommuteTools, COMMUTE_URI
from KIDSic.dto.commute import CommuteQuery
from KIDSic.dto.day_route import DayJourneyRequest
from KIDSic.integrations.concrete.address import LocalAddressLookup, normalized_address
from KIDSic.services.concrete.commute import CommuteService
from KIDSic.services.concrete.day_route import DayRouteService
from test_journey import journey
from test_mcp_server import connected


def criteria(**changes):
    return dict(city='Rijeka', home={'lat':45.338,'lon':14.410},
                work={'lat':45.3271,'lon':14.4422}, departure='2026-11-05T07:00',
                mode='TRANSIT') | changes


class RecommendationTests(unittest.IsolatedAsyncioTestCase):
    async def test_ranks_every_mapped_facility_and_returns_best_plus_three(self):
        query=DayJourneyRequest(**{k:v for k,v in criteria().items() if k!='city'})
        facilities=[SimpleNamespace(id=f'id{i}',geometry=SimpleNamespace(coordinates=(14.42+i*.001,45.33)),
            properties=SimpleNamespace(address=f'Test {i}',location_name=f'Object {i}',location_role='facility'))
            for i in range(6)]
        locations=SimpleNamespace(list_locations=AsyncMock(return_value=SimpleNamespace(
            features=facilities,metadata=SimpleNamespace(total=8))))
        active=0
        peak=0
        class Planner:
            async def plan(self, origin, destination, departure, mode):
                nonlocal active,peak
                active+=1
                peak=max(peak,active)
                try:
                    await asyncio.sleep(.001)
                    if origin==query.home and destination==query.work:
                        return journey(departure,5)
                    if origin==query.home:
                        return journey(departure,5)
                    return journey(departure,round((14.43-origin.lon)*1000))
                finally:
                    active-=1
        result=await DayRouteService(locations,Planner()).recommend(query)
        self.assertEqual([r['facility_id'] for r in result['results']],['id5','id4','id3','id2'])
        self.assertEqual((result['searched'],result['reachable'],result['excluded']),(6,6,2))
        self.assertLessEqual(peak,4)
        self.assertEqual(result['results'][0]['elapsed_seconds'],20*60)
        self.assertEqual(result['home'],query.home.model_dump())

    async def test_waiting_and_dropoff_are_included_in_elapsed_time(self):
        query=DayJourneyRequest(**{k:v for k,v in criteria().items() if k!='city'})
        facility=SimpleNamespace(id='one',geometry=SimpleNamespace(coordinates=(14.42,45.33)),
            properties=SimpleNamespace(address='Test 1',location_name='One',location_role='facility'))
        locations=SimpleNamespace(list_locations=AsyncMock(return_value=SimpleNamespace(
            features=[facility],metadata=SimpleNamespace(total=1))))
        planner=SimpleNamespace(plan=AsyncMock(side_effect=[
            journey(query.departure+timedelta(minutes=5),10),
            journey(query.departure+timedelta(minutes=5),10),
            journey(query.departure+timedelta(minutes=30),20)]))
        result=await DayRouteService(locations,planner).recommend(query)
        option=result['results'][0]
        self.assertEqual(option['elapsed_seconds'],50*60)
        self.assertEqual(option['extra_seconds'],35*60)
        self.assertEqual(planner.plan.await_args_list[2].args[2],query.departure+timedelta(minutes=25))
        self.assertIsNone(option['opening_hours'])

    async def test_unreachable_facilities_are_counted_without_fabricating_options(self):
        query=DayJourneyRequest(**{k:v for k,v in criteria().items() if k!='city'})
        facility=SimpleNamespace(id='one',geometry=SimpleNamespace(coordinates=(14.42,45.33)),
            properties=SimpleNamespace(address='Test 1',location_name='One',location_role='facility'))
        locations=SimpleNamespace(list_locations=AsyncMock(return_value=SimpleNamespace(
            features=[facility],metadata=SimpleNamespace(total=1))))
        planner=SimpleNamespace(plan=AsyncMock(return_value=None))
        result=await DayRouteService(locations,planner).recommend(query)
        self.assertEqual(result['results'],[])
        self.assertEqual((result['searched'],result['without_route']),(1,1))
        self.assertEqual(planner.plan.await_count,2)

    async def test_ambiguity_or_partial_match_never_calls_routing(self):
        routes=SimpleNamespace(recommend=AsyncMock())
        lookup=SimpleNamespace(find=lambda q:[{'label':'Synthetic 1','point':{'lat':45.33,'lon':14.43},'match':'partial'}])
        result=await CommuteService(routes,lookup).recommend(CommuteQuery(**criteria(home='Synthetic')))
        self.assertEqual(result['status'],'clarification_required')
        self.assertIn('home',result['unresolved'])
        routes.recommend.assert_not_awaited()

    async def test_exact_addresses_become_sourced_points(self):
        rows={'Home 1':{'label':'Home 1','point':{'lat':45.33,'lon':14.41},'match':'exact'},
              'Work 2':{'label':'Work 2','point':{'lat':45.33,'lon':14.44},'match':'exact'}}
        routes=SimpleNamespace(recommend=AsyncMock(return_value={'results':[]}))
        service=CommuteService(routes,SimpleNamespace(find=lambda q:[rows[q]]))
        result=await service.recommend(CommuteQuery(**criteria(home='Home 1',work='Work 2')))
        query=routes.recommend.await_args.args[0]
        self.assertEqual((query.home.lon,query.work.lon),(14.41,14.44))
        self.assertEqual(result['status'],'no_route')
        self.assertIn('10 minuta',result['notice'])


class AddressTests(unittest.TestCase):
    def test_exact_number_and_diacritics_and_partial_are_distinct(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'addresses.sqlite'
            with closing(sqlite3.connect(path)) as db, db:
                db.execute('CREATE TABLE addresses (id TEXT,label TEXT,normalized TEXT,lat REAL,lon REAL)')
                for i,name in enumerate(['Ulica Žrtava fašizma 1','Ulica Žrtava fašizma 11']):
                    db.execute('INSERT INTO addresses VALUES (?,?,?,?,?)',(str(i),name,normalized_address(name),45.33,14.43))
            lookup=LocalAddressLookup(path)
            exact=lookup.find('Zrtava fasizma 1, Rijeka')
            self.assertEqual(len(exact),1)
            self.assertEqual(exact[0]['match'],'exact')
            self.assertEqual(len(lookup.find('Žrtava fašizma')),2)
            self.assertTrue(all(r['match']=='partial' for r in lookup.find('Žrtava fašizma')))
            self.assertEqual(lookup.find('Unknown 99'),[])


class CommuteToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_protocol_exposes_route_resource_and_model_summary(self):
        service=SimpleNamespace(recommend=AsyncMock(return_value={
            'status':'ok','results':[{'facility_id':'one','name':'Synthetic','journeys':[{'geometry':'private shape'}],
                                      'point':{'lat':45.33,'lon':14.43}}],
            'home':{'lat':45.33,'lon':14.41},'work':{'lat':45.33,'lon':14.44},'notice':'test'}))
        async with connected(SimpleNamespace(list_locations=AsyncMock()),commute_service=service) as (session,_):
            tool=next(t for t in (await session.list_tools()).tools if t.name==CommuteTools.name)
            self.assertEqual(tool.meta['ui']['resourceUri'],COMMUTE_URI)
            self.assertIn('mode',tool.inputSchema['required'])
            result=await session.call_tool(tool.name,criteria())
            self.assertFalse(result.isError)
            self.assertNotIn('home',result.structuredContent)
            self.assertNotIn('journeys',result.structuredContent['results'][0])
            self.assertIn('home',result.meta['commute'])
            asset=(await session.read_resource(COMMUTE_URI)).contents[0]
            self.assertIn('Commute map',asset.text)
            self.assertEqual(asset.meta['ui']['csp']['connectDomains'],['https://tile.openstreetmap.org'])
        service.recommend.assert_awaited_once()

    async def test_invalid_missing_mode_and_failures_are_actionable(self):
        service=SimpleNamespace(recommend=AsyncMock())
        tool=CommuteTools(lambda:service)
        for bad in ({},criteria(city='Zagreb'),criteria(departure='07:00'),
                    {k:v for k,v in criteria().items() if k!='mode'},criteria(facility_ids=['one'])):
            result=await tool.call_tool(tool.name,bad)
            self.assertTrue(result.isError)
            self.assertIn('invalid_commute',result.content[0].text)
        service.recommend.assert_not_awaited()
        service.recommend.side_effect=RuntimeError('Private address')
        result=await tool.call_tool(tool.name,criteria())
        self.assertTrue(result.isError)
        self.assertNotIn('Private address',result.content[0].text)
