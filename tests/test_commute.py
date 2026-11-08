"""Commute tests cover full-catalogue ranking and clarification before routing."""

import asyncio
import sqlite3
import unittest
from contextlib import closing
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock

from support.commute import criteria, facility
from support.journeys import journey
from support.mcp import connected

from KIDSic.api.apps.map_resource import UI_URI
from KIDSic.api.commute_tools import COMMUTE_URI, CommuteTools
from KIDSic.dto.commute import CommuteQuery
from KIDSic.dto.day_route import DayJourneyRequest
from KIDSic.integrations.concrete.address import LocalAddressLookup, normalized_address
from KIDSic.services.concrete.commute import CommuteService
from KIDSic.services.concrete.day_route import DayRouteService


class RecommendationTests(unittest.IsolatedAsyncioTestCase):
    async def test_ranks_every_mapped_facility_and_returns_best_plus_three(self):
        query = DayJourneyRequest(
            **{k: v for k, v in criteria().items() if k != "city"}
        )
        facilities = [
            facility(f"id{i}", 14.42 + i * 0.001, f"Object {i}") for i in range(6)
        ]
        locations = SimpleNamespace(
            list_locations=AsyncMock(
                return_value=SimpleNamespace(
                    features=facilities, metadata=SimpleNamespace(total=8)
                )
            )
        )
        active = 0
        peak = 0

        class Planner:
            async def plan(self, origin, destination, departure, mode):
                nonlocal active, peak
                active += 1
                peak = max(peak, active)
                try:
                    await asyncio.sleep(0.001)
                    if origin == query.home and destination == query.work:
                        return journey(departure, 5)
                    if origin == query.home:
                        return journey(departure, 5)
                    return journey(departure, round((14.43 - origin.lon) * 1000))
                finally:
                    active -= 1

        result = await DayRouteService(locations, Planner()).recommend(query)
        self.assertEqual(
            [r["facility_id"] for r in result["results"]], ["id5", "id4", "id3", "id2"]
        )
        self.assertEqual(
            (result["searched"], result["reachable"], result["excluded"]), (6, 6, 2)
        )
        self.assertLessEqual(peak, 4)
        self.assertEqual(result["results"][0]["elapsed_seconds"], 20 * 60)
        self.assertEqual(result["home"], query.home.model_dump())
        self.assertEqual(
            [f["id"] for f in result["locations"]["features"]],
            ["id5", "id4", "id3", "id2"],
        )
        for limit in (1, 3, 6, 30):
            limited = await DayRouteService(locations, Planner()).recommend(
                query.model_copy(update={"top_k": limit})
            )
            self.assertEqual(len(limited["results"]), min(limit, 6))
            self.assertEqual(limited["locations"]["metadata"]["total"], min(limit, 6))
            self.assertEqual(limited["searched"], 6)
            self.assertEqual(limited["top_k"], limit)

    async def test_ranks_only_the_named_shortlist_and_finds_names_like_the_map(self):
        query = DayJourneyRequest(
            **{k: v for k, v in criteria().items() if k != "city"}
        )
        facilities = [
            facility(f"id{i}", 14.42 + i * 0.001, f"Object {i}") for i in range(4)
        ]

        async def list_locations(location_query):

            found = [
                f
                for f in facilities
                if location_query.q.casefold() in f.properties.location_name.casefold()
            ]
            return SimpleNamespace(features=found, metadata=SimpleNamespace(total=6))

        planner = SimpleNamespace(
            plan=AsyncMock(
                side_effect=lambda origin, destination, departure, mode: journey(
                    departure,
                    5 if origin == query.home else round((14.43 - origin.lon) * 1000),
                )
            )
        )
        routes = DayRouteService(
            SimpleNamespace(list_locations=list_locations), planner
        )
        result = await routes.recommend(query, ["id1", "id3", "unknown"])
        self.assertEqual([r["facility_id"] for r in result["results"]], ["id3", "id1"])
        self.assertEqual(
            (
                result["searched"],
                result["reachable"],
                result["excluded"],
                result["scope"],
            ),
            (2, 2, 0, "selected"),
        )
        self.assertEqual(
            [f["id"] for f in result["locations"]["features"]], ["id3", "id1"]
        )
        self.assertEqual((await routes.recommend(query))["scope"], "all")
        self.assertEqual([str(f.id) for f in await routes.find("object 2")], ["id2"])
        self.assertEqual(len(await routes.find("Object")), 4)
        self.assertEqual(
            [str(f.id) for f in await routes.find("id0")], ["id0"]
        )

    async def test_waiting_and_dropoff_are_included_in_elapsed_time(self):
        query = DayJourneyRequest(
            **{k: v for k, v in criteria().items() if k != "city"}
        )
        item = facility("one", name="One")
        locations = SimpleNamespace(
            list_locations=AsyncMock(
                return_value=SimpleNamespace(
                    features=[item], metadata=SimpleNamespace(total=1)
                )
            )
        )
        planner = SimpleNamespace(
            plan=AsyncMock(
                side_effect=[
                    journey(query.departure + timedelta(minutes=5), 10),
                    journey(query.departure + timedelta(minutes=5), 10),
                    journey(query.departure + timedelta(minutes=30), 20),
                ]
            )
        )
        result = await DayRouteService(locations, planner).recommend(query)
        option = result["results"][0]
        self.assertEqual(option["elapsed_seconds"], 50 * 60)
        self.assertEqual(option["extra_seconds"], 35 * 60)
        self.assertEqual(
            planner.plan.await_args_list[2].args[2],
            query.departure + timedelta(minutes=25),
        )
        self.assertIsNone(option["opening_hours"])

    async def test_unreachable_facilities_are_counted_without_fabricating_options(self):
        query = DayJourneyRequest(
            **{k: v for k, v in criteria().items() if k != "city"}
        )
        item = facility("one", name="One")
        locations = SimpleNamespace(
            list_locations=AsyncMock(
                return_value=SimpleNamespace(
                    features=[item], metadata=SimpleNamespace(total=1)
                )
            )
        )
        planner = SimpleNamespace(plan=AsyncMock(return_value=None))
        result = await DayRouteService(locations, planner).recommend(query)
        self.assertEqual(result["results"], [])
        self.assertEqual((result["searched"], result["without_route"]), (1, 1))
        self.assertEqual(planner.plan.await_count, 2)

    async def test_ambiguity_or_partial_match_never_calls_routing(self):
        routes = SimpleNamespace(recommend=AsyncMock())
        lookup = SimpleNamespace(
            find=lambda q: [
                {
                    "label": "Synthetic 1",
                    "point": {"lat": 45.33, "lon": 14.43},
                    "match": "partial",
                }
            ]
        )
        result = await CommuteService(routes, lookup).recommend(
            CommuteQuery(**criteria(home="Synthetic"))
        )
        self.assertEqual(result["status"], "clarification_required")
        self.assertIn("home", result["unresolved"])
        routes.recommend.assert_not_awaited()

    async def test_exact_addresses_become_sourced_points(self):
        rows = {
            "Home 1": {
                "label": "Home 1",
                "point": {"lat": 45.33, "lon": 14.41},
                "match": "exact",
            },
            "Work 2": {
                "label": "Work 2",
                "point": {"lat": 45.33, "lon": 14.44},
                "match": "exact",
            },
        }
        routes = SimpleNamespace(recommend=AsyncMock(return_value={"results": []}))
        service = CommuteService(routes, SimpleNamespace(find=lambda q: [rows[q]]))
        result = await service.recommend(
            CommuteQuery(**criteria(home="Home 1", work="Work 2", top_k=2))
        )
        query = routes.recommend.await_args.args[0]
        self.assertEqual((query.home.lon, query.work.lon), (14.41, 14.44))
        self.assertEqual(query.top_k, 2)
        self.assertEqual(result["status"], "no_route")
        self.assertIn("10 minuta", result["notice"])

    async def test_named_kindergartens_resolve_or_ask_before_ranking(self):
        point = {"lat": 45.33, "lon": 14.41}
        named = {
            "Mala Vila": [facility("mv", name="Mala Vila")],
            "Potok": [facility("p1", name="Potok 1"), facility("p2", name="Potok 2")],
            "Nema": [],
        }
        routes = SimpleNamespace(
            find=AsyncMock(side_effect=lambda name, city: named[name]),
            recommend=AsyncMock(return_value={"results": []}),
        )
        service = CommuteService(routes, SimpleNamespace(find=lambda q: []))
        result = await service.recommend(
            CommuteQuery(
                **criteria(
                    home=point, work=point, kindergartens=["Mala Vila", "Potok", "Nema"]
                )
            )
        )
        self.assertEqual(result["status"], "clarification_required")
        self.assertEqual(
            [
                (u["query"], u["matches"], [c["id"] for c in u["candidates"]])
                for u in result["unresolved"]["kindergartens"]
            ],
            [("Potok", 2, ["p1", "p2"]), ("Nema", 0, [])],
        )
        routes.recommend.assert_not_awaited()
        named["Potok"] = [named["Potok"][1]]
        result = await service.recommend(
            CommuteQuery(
                **criteria(home=point, work=point, kindergartens=["Mala Vila", "Potok"])
            )
        )
        self.assertEqual(routes.recommend.await_args.args[1], ["mv", "p2"])
        self.assertIn("samo vrtići koje je korisnik naveo", result["notice"])
        await service.recommend(CommuteQuery(**criteria(home=point, work=point)))
        self.assertIsNone(routes.recommend.await_args.args[1])


class AddressTests(unittest.TestCase):
    def test_exact_number_and_diacritics_and_partial_are_distinct(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "addresses.sqlite"
            with closing(sqlite3.connect(path)) as db, db:
                db.execute(
                    "CREATE TABLE addresses (id TEXT,label TEXT,normalized TEXT,lat REAL,lon REAL)"
                )
                for i, name in enumerate(
                    ["Ulica Žrtava fašizma 1", "Ulica Žrtava fašizma 11"]
                ):
                    db.execute(
                        "INSERT INTO addresses VALUES (?,?,?,?,?)",
                        (str(i), name, normalized_address(name), 45.33, 14.43),
                    )
            lookup = LocalAddressLookup(path)
            exact = lookup.find("Zrtava fasizma 1, Rijeka")
            self.assertEqual(len(exact), 1)
            self.assertEqual(exact[0]["match"], "exact")
            self.assertEqual(len(lookup.find("Žrtava fašizma")), 2)
            self.assertTrue(
                all(r["match"] == "partial" for r in lookup.find("Žrtava fašizma"))
            )
            self.assertEqual(lookup.find("Unknown 99"), [])


class CommuteToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_protocol_exposes_route_resource_and_model_summary(self):
        service = SimpleNamespace(
            recommend=AsyncMock(
                return_value={
                    "status": "ok",
                    "results": [
                        {
                            "facility_id": "one",
                            "name": "Synthetic",
                            "journeys": [{"geometry": "private shape"}],
                            "point": {"lat": 45.33, "lon": 14.43},
                        }
                    ],
                    "locations": {"private": "canonical UI locations"},
                    "home": {"lat": 45.33, "lon": 14.41},
                    "work": {"lat": 45.33, "lon": 14.44},
                    "notice": "test",
                }
            )
        )
        async with connected(
            SimpleNamespace(list_locations=AsyncMock()), commute_service=service
        ) as (session, _):
            tool = next(
                t
                for t in (await session.list_tools()).tools
                if t.name == CommuteTools.name
            )
            self.assertEqual(tool.meta["ui"]["resourceUri"], COMMUTE_URI)
            self.assertIn("mode", tool.inputSchema["required"])
            result = await session.call_tool(tool.name, criteria())
            self.assertFalse(result.isError)
            self.assertNotIn("home", result.structuredContent)
            self.assertNotIn("locations", result.structuredContent)
            self.assertIn("locations", result.meta["commute"])
            self.assertNotIn("journeys", result.structuredContent["results"][0])
            self.assertIn("home", result.meta["commute"])
            asset = (await session.read_resource(COMMUTE_URI)).contents[0]
            self.assertEqual(COMMUTE_URI, UI_URI)
            self.assertIn("KIDSic map", asset.text)
            self.assertEqual(len((await session.list_resources()).resources), 1)
            self.assertEqual(tool.inputSchema["properties"]["top_k"]["default"], 4)
            self.assertIn("kindergartens", tool.inputSchema["properties"])
            self.assertEqual(
                asset.meta["ui"]["csp"]["connectDomains"],
                ["https://tile.openstreetmap.org"],
            )
        service.recommend.assert_awaited_once()

    async def test_invalid_missing_mode_and_failures_are_actionable(self):
        service = SimpleNamespace(recommend=AsyncMock())
        tool = CommuteTools(lambda city: service)
        for bad in (
            {},
            criteria(city="Zagreb"),
            criteria(departure="07:00"),
            {k: v for k, v in criteria().items() if k != "mode"},
            criteria(facility_ids=["one"]),
            criteria(top_k=0),
            criteria(top_k=True),
            criteria(top_k="3"),
            criteria(kindergartens=[]),
            criteria(kindergartens=["x"]),
            criteria(kindergartens=[f"Vrtić {i}" for i in range(21)]),
        ):
            result = await tool.call_tool(tool.name, bad)
            self.assertTrue(result.isError)
            self.assertIn("invalid_commute", result.content[0].text)
        service.recommend.assert_not_awaited()
        try:
            raise ConnectionError("Zametska 6")
        except ConnectionError as cause:
            failure = RuntimeError("Private address")
            failure.__cause__ = cause
        service.recommend.side_effect = failure
        with self.assertLogs("KIDSic.api.commute_tools", "ERROR") as logs:
            result = await tool.call_tool(tool.name, criteria())
        self.assertTrue(result.isError)
        self.assertNotIn("Private address", result.content[0].text)
        log = " ".join(logs.output)
        self.assertIn(
            "RuntimeError <- ConnectionError", log
        )
        self.assertNotIn("Private address", log)
        self.assertNotIn("Zametska", log)
