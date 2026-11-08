"""Source fixtures build fresh clients and services using synthetic records."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from KIDSic.dto.ckan import CkanPackage
from KIDSic.services.concrete.parsers import default_parsers
from KIDSic.services.concrete.source import SourceService
from KIDSic.services.concrete.source_normalizer import SourceRecordNormalizer
from KIDSic.services.concrete.source_planner import SourceRegistrationPlanner

NATIONAL = {
    "Naziv": 'Dječji vrtić "Primjer"',
    "Adresa": "Primjer 1",
    "Mjesto": "Varaždin",
    "ePosta": "",
    "Telefon": "",
    "Zupanija": "Varaždinska županija ",
    "PostanskiBroj": "42000",
}


MUNICIPAL = {
    "Id": 1,
    "Naziv": "DV Primjer-matični objekt",
    "Adresa": "Primjer 1",
    "X": "15,9452",
    "Y": "45.8017",
    "Web": None,
    "Email": "test@example.invalid",
    "Telefon": "",
    "TipVrtica": "Matični",
    "VrstaVrtica": "Gradski DV",
    "GradskaCetvrt": "Trešnjevka-Sjever",
}


def source_service(clients, definitions, work=None, *, normalizer=None):
    """source_service builds a SourceService with the built-in schemas."""
    return SourceService(
        clients,
        definitions,
        work,
        planner=SourceRegistrationPlanner(),
        normalizer=normalizer or SourceRecordNormalizer(default_parsers()),
    )


def source_client(name="national"):
    payload = json.loads(
        (Path(__file__).parents[1] / f"fixtures/ckan_{name}.json").read_text()
    )
    return SimpleNamespace(
        get_package=AsyncMock(
            return_value=CkanPackage.model_validate(payload["result"])
        ),
        download_records=AsyncMock(return_value=[copy.deepcopy(NATIONAL)]),
    )
