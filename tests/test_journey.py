"""Journey tests validate commute inputs and the OTP transport contract."""

import unittest
from datetime import datetime, timedelta

import httpx
from pydantic import ValidationError

from KIDSic.dto.day_route import ZAGREB, DayJourneyRequest, DayPoint
from KIDSic.integrations.concrete.otp import OtpJourneyPlanner
from KIDSic.integrations.interfaces.journey import RoutingUnavailable


def request_data(**changes):
    return dict(
        home={"lat": 45.33, "lon": 14.41},
        work={"lat": 45.33, "lon": 14.44},
        departure="2026-11-05T07:00",
        **changes,
    )


class DayRequestTests(unittest.TestCase):
    def test_local_time_and_region(self):
        query = DayJourneyRequest(**request_data())
        self.assertEqual(query.departure.utcoffset(), timedelta(hours=1))
        self.assertEqual(
            DayJourneyRequest(
                **{**request_data(), "departure": "2026-11-05T06:00Z"}
            ).departure,
            query.departure,
        )
        for updates in (
            {"home": {"lat": 45.81, "lon": 15.98}},
            {"dropoff_minutes": True},
            {"departure": "2026-07-02T07:00"},
            {"mode": "CAR"},
            {"home": {"lat": float("nan"), "lon": 14.4}},
        ):
            with self.subTest(updates=updates), self.assertRaises(ValidationError):
                DayJourneyRequest(**{**request_data(), **updates})


class OtpTests(unittest.IsolatedAsyncioTestCase):
    async def test_graphql_variables_and_earliest_arrival(self):
        start = datetime(2026, 11, 5, 7, tzinfo=ZAGREB)

        def itinerary(minutes):
            def ms(d):
                return int(d.timestamp() * 1000)

            return {
                "startTime": ms(start),
                "endTime": ms(start + timedelta(minutes=minutes)),
                "legs": [
                    {
                        "mode": "BUS",
                        "startTime": ms(start),
                        "endTime": ms(start + timedelta(minutes=minutes)),
                        "from": {"name": "A"},
                        "to": {"name": "B"},
                        "route": {"shortName": "7"},
                        "legGeometry": {"points": "test"},
                    }
                ],
            }

        def respond(request):
            import json

            variables = json.loads(request.content)["variables"]
            self.assertEqual(variables["time"], "07:00:00")
            self.assertEqual(
                variables["modes"], [{"mode": "WALK"}, {"mode": "TRANSIT"}]
            )
            return httpx.Response(
                200,
                json={
                    "data": {"plan": {"itineraries": [itinerary(30), itinerary(20)]}}
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
            result = await OtpJourneyPlanner(http, "http://otp.local/otp/gtfs/v1").plan(
                DayPoint(lat=45.33, lon=14.41),
                DayPoint(lat=45.33, lon=14.44),
                start,
                "TRANSIT",
            )
        self.assertEqual(result.arrival, start + timedelta(minutes=20))
        self.assertEqual(result.legs[0].line, "7")

    async def test_empty_is_no_route_but_errors_are_unavailable(self):
        for payload, fails in [
            ({"data": {"plan": {"itineraries": []}}}, False),
            ({"errors": [{"message": "internal"}]}, True),
            ({"data": {}}, True),
        ]:
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(
                    lambda r, payload=payload: httpx.Response(200, json=payload)
                )
            ) as http:
                planner = OtpJourneyPlanner(http, "http://otp.local")
                args = (
                    DayPoint(lat=45.33, lon=14.41),
                    DayPoint(lat=45.33, lon=14.44),
                    datetime(2026, 11, 5, 7, tzinfo=ZAGREB),
                    "WALK",
                )
                if fails:
                    with self.assertRaises(RoutingUnavailable):
                        await planner.plan(*args)
                else:
                    self.assertIsNone(await planner.plan(*args))
