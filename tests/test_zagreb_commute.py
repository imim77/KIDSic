"""Zagreb commute tests prevent city, timetable and source leakage from Rijeka."""

import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock

from pydantic import ValidationError
from support.commute import criteria, facility
from support.journeys import journey
from support.mcp import connected

from KIDSic.api.commute_tools import CommuteTools
from KIDSic.config.routing import ROUTING_CITIES
from KIDSic.dto.commute import CommuteQuery
from KIDSic.dto.day_route import DayJourneyRequest
from KIDSic.dto.location import LocationFeature
from KIDSic.integrations.concrete.address import LocalAddressLookup, normalized_address
from KIDSic.services.concrete.commute import CommuteService
from KIDSic.services.concrete.day_route import DayRouteService


def zagreb(**changes):
    return criteria(
        city="Zagreb",
        home={"lat": 45.81, "lon": 15.96},
        work={"lat": 45.81, "lon": 16.01},
        **changes,
    )


class ZagrebRequestTests(unittest.TestCase):
    def test_city_specific_coordinates_and_actual_service_dates(self):
        for departure in ("2026-10-21T07:00", "2026-12-31T07:00"):
            self.assertEqual(CommuteQuery(**zagreb(departure=departure)).city, "Zagreb")
        for changes in (
            {"departure": "2027-01-01T07:00"},
            {"departure": "2026-10-20T07:00"},
            {"home": {"lat": 45.33, "lon": 14.42}},
            {"city": "Osijek"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                CommuteQuery(**(zagreb() | changes))
        with self.assertRaises(ValidationError):
            CommuteQuery(**criteria(departure="2026-12-01T07:00"))
        with self.assertRaises(ValidationError):
            CommuteQuery(**{k: v for k, v in zagreb().items() if k != "city"})

    def test_zagreb_address_suffix_is_resolved_only_in_its_city_index(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "addresses.sqlite"
            with closing(sqlite3.connect(path)) as db, db:
                db.execute(
                    "CREATE TABLE addresses (id TEXT,label TEXT,normalized TEXT,lat REAL,lon REAL)"
                )
                db.execute(
                    "INSERT INTO addresses VALUES (?,?,?,?,?)",
                    (
                        "1",
                        "Ilica 10",
                        normalized_address("Ilica 10", "Zagreb"),
                        45.81,
                        15.97,
                    ),
                )
            lookup = LocalAddressLookup(path, "Zagreb")
            self.assertEqual(lookup.find("Ilica 10, 10000 Zagreb")[0]["match"], "exact")
            self.assertEqual(lookup.find("Ilica 10, Rijeka"), [])
            self.assertEqual(lookup.find("Ilica")[0]["match"], "partial")


class ZagrebRecommendationTests(unittest.IsolatedAsyncioTestCase):
    async def test_ranks_zagreb_catalogue_with_zet_provenance(self):
        request = DayJourneyRequest(**zagreb(departure="2026-12-01T07:00"))
        item = LocationFeature(
            id="zg",
            geometry={"coordinates": (15.98, 45.81)},
            properties=facility("zg").properties.model_copy(update={"city": "Zagreb"}),
        )
        locations = SimpleNamespace(
            list_locations=AsyncMock(
                return_value=SimpleNamespace(
                    features=[item, facility("ri")], metadata=SimpleNamespace(total=2)
                )
            )
        )
        planner = SimpleNamespace(
            plan=AsyncMock(
                side_effect=lambda origin, destination, departure, mode: journey(
                    departure, 5, "TRAM"
                )
            )
        )
        routes = DayRouteService(locations, planner)
        result = await routes.recommend(request)
        self.assertEqual(result["city"], "Zagreb")
        self.assertEqual((result["searched"], result["excluded"]), (1, 1))
        self.assertEqual(result["results"][0]["facility_id"], "zg")
        self.assertEqual(result["results"][0]["elapsed_seconds"], 20 * 60)
        self.assertEqual(
            result["sources"]["gtfs_url"], ROUTING_CITIES["Zagreb"].gtfs_url
        )
        self.assertEqual(result["sources"]["license"], "Otvorena dozvola RH")
        self.assertEqual(result["sources"]["service_end"], "2026-12-31")
        self.assertTrue(
            all(
                call.args[0].city == "Zagreb"
                for call in locations.list_locations.await_args_list
            )
        )
        self.assertEqual([str(f.id) for f in await routes.find("zg", "Zagreb")], ["zg"])

    async def test_city_reaches_address_resolution_and_shortlist(self):
        routes = SimpleNamespace(find=AsyncMock(return_value=[]), recommend=AsyncMock())
        lookup = SimpleNamespace(
            find=lambda q: [
                {"label": q, "point": {"lat": 45.81, "lon": 15.98}, "match": "exact"}
            ]
        )
        query = CommuteQuery(
            **(zagreb() | {"home": "Ilica 10", "kindergartens": ["Bajka"]})
        )
        result = await CommuteService(routes, lookup).recommend(query)
        self.assertEqual(result["status"], "clarification_required")
        routes.find.assert_awaited_once_with("Bajka", "Zagreb")
        routes.recommend.assert_not_awaited()
        query = CommuteQuery(**(zagreb() | {"home": "Ilica 10"}))
        routes.recommend.return_value = {"results": []}
        await CommuteService(routes, lookup).recommend(query)
        self.assertEqual(routes.recommend.await_args.args[0].city, "Zagreb")

    async def test_mcp_accepts_zagreb_and_dispatches_to_selected_service(self):
        service = SimpleNamespace(
            recommend=AsyncMock(return_value={"status": "no_route", "results": []})
        )
        cities = []

        def provider(city):
            cities.append(city)
            return service

        result = await CommuteTools(provider).call_tool(CommuteTools.name, zagreb())
        self.assertFalse(result.isError)
        self.assertEqual(cities, ["Zagreb"])
        async with connected(
            SimpleNamespace(list_locations=AsyncMock()), commute_service=service
        ) as (session, _):
            result = await session.call_tool(CommuteTools.name, zagreb())
            self.assertFalse(result.isError)
            tools = (await session.list_tools()).tools
            tool = next(t for t in tools if t.name == CommuteTools.name)
            self.assertIn("Zagreb", tool.inputSchema["properties"]["city"]["enum"])
