"""RoutingCity keeps each city's reviewed timetable and street coverage together."""
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class RoutingCity:
    name: str
    key: str
    bbox: tuple[float, float, float, float]
    service_start: date
    service_end: date
    gtfs_url: str
    gtfs_sha256: str
    publisher: str
    license: str
    license_url: str
    gtfs_filename: str
    port: int
    retrieved_on: date

    def contains(self, lat: float, lon: float) -> bool:
        west, south, east, north = self.bbox
        return south <= lat <= north and west <= lon <= east

    @property
    def directory(self) -> Path:
        return Path('routing/data') / ('' if self.key == 'rijeka' else self.key)


ROUTING_CITIES = {
    'Rijeka': RoutingCity('Rijeka', 'rijeka', (14.20, 45.20, 14.65, 45.45),
        date(2026, 10, 9), date(2026, 11, 8),
        'https://gitlab.com/api/v4/projects/vekejsn%2Fgtfs-generators/'
        'packages/generic/rijeka-gtfs/latest/autotrolej_gtfs.zip',
        'e2d9357c5f020d6d4081ba114509d89f51a33dd224d09aae09ff6c1e4c0849bd',
        'vekejsn', 'CC-BY-4.0', 'https://transitous.org/sources/#croatia',
        'autotrolej-gtfs.zip', 18080, date(2026, 11, 5)),
    'Zagreb': RoutingCity('Zagreb', 'zagreb', (15.70, 45.60, 16.30, 46.00),
        date(2026, 10, 21), date(2026, 12, 31),
        'https://www.zet.hr/gtfs-scheduled/scheduled-000-000397.zip',
        '2ddf4051147837545bc1b77af5a82bc8961096da630b11fe7a1079ce3654edf8',
        'Zagrebački električni tramvaj d.o.o.', 'Otvorena dozvola RH',
        'https://www.zet.hr/preuzimanja/odredbe/datoteke-u-gtfs-formatu/669',
        'zet-gtfs.zip', 18081, date(2026, 11, 6)),
    'Šibenik': RoutingCity('Šibenik', 'sibenik', (15.70, 43.60, 16.05, 43.85),
        date(2026, 9, 7), date(2027, 6, 7),
        'https://www.gradski-parking.hr/upload/stranice/2022/08/2022-08-30/89/gtfs.zip',
        '6fd33879adc8a57e66fab75dbdcebc9136b383be0e7a7274e0accb4561530128',
        'Gradski parking d.o.o. Šibenik', 'Otvorena dozvola RH',
        'https://www.gradski-parking.hr/stranice/datoteke-u-gtfs-formatu/105.html',
        'sibenik-gtfs.zip', 18082, date(2026, 11, 6)),
}
