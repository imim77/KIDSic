"""Rijeka fixtures load the synthetic catalogue and its pinned metadata."""

import csv
import json
from pathlib import Path

from KIDSic.dto.ckan import CkanPackage
from KIDSic.dto.source import PlannedSource, SourceDefinition

FIXTURES = Path(__file__).parents[1] / "fixtures"


def rijeka_records():
    return list(
        csv.DictReader(
            (FIXTURES / "rijeka.csv").read_text().splitlines(), delimiter=";"
        )
    )


def rijeka_source():
    package = CkanPackage.model_validate(
        json.loads((FIXTURES / "ckan_rijeka.json").read_text())["result"]
    )
    return PlannedSource(
        SourceDefinition(
            "rijeka-kindergartens",
            "https://data.rijeka.hr",
            "djecji-vrtici",
            "rijeka-kindergartens",
            resource_format="csv",
            resource_id=package.resources[0].id,
            license_id="cc-by",
            csv_encoding="cp1250",
        ),
        package,
        package.resources[0],
    )
