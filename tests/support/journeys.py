"""Journey fixtures provide deterministic routes without an OTP server."""

from datetime import timedelta

from KIDSic.dto.day_route import Journey, RouteLeg


def journey(start, minutes, mode="WALK"):
    end = start + timedelta(minutes=minutes)
    return Journey(
        departure=start,
        arrival=end,
        legs=[
            RouteLeg(
                mode=mode,
                departure=start,
                arrival=end,
                from_name="Synthetic A",
                to_name="Synthetic B",
            )
        ],
    )
