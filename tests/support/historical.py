"""Historical fixtures describe synthetic programs and published vacancies."""

from KIDSic.config.historical import zagreb_historical_sources
from KIDSic.dto.ckan import CkanPackage, CkanResource
from KIDSic.services.concrete.historical import HistoricalService
from KIDSic.services.concrete.historical_layouts import default_historical_layouts
from KIDSic.services.concrete.historical_parser import HistoricalTableParser
from KIDSic.services.concrete.source_planner import SourceRegistrationPlanner

DEFINITIONS = zagreb_historical_sources("https://example.invalid")


PROGRAMS = [
    ["Name", "Description", "VRSTA", "PROGRAMI"],
    [
        "DJEČJI VRTIĆ PRIMJER",
        "Primjer ulica 1",
        "Gradski vrtić",
        "Montessori;engleski jezik;Montessori",
    ],
    ["DJEČJI VRTIĆ PRIMJER", "Druga 2", "", "/"],
]


FOOTER = "PODACI O SLOBODNIM MJESTIMA STANJE NA DAN 1.1.2025."


def historical_parser():
    return HistoricalTableParser(default_historical_layouts())


def historical_service(clients, definitions, work=None):
    """historical_service builds a HistoricalService with Zagreb's layouts."""
    return HistoricalService(
        clients,
        definitions,
        work,
        parser=historical_parser(),
        planner=SourceRegistrationPlanner(),
    )


def municipal_table():
    top = [
        "Gradska četvrt",
        "Naziv dječjeg vrtića",
        "Područni objekti u drugim gradskim četvrtima",
    ] + [""] * 20
    ages = [
        "",
        "",
        "",
        "od 1 do 2 godine",
        "",
        "od 2 do 3 godine",
        "",
        "od 1 do 3 godine (mješovita)",
        "",
        "UKUPNO",
        "",
        "",
        "od 3 do 4 godine",
        "",
        "od 4 do 5 godine",
        "",
        "od 5 godina do OŠ",
        "",
        "od 3 godine do OŠ (mješovita)",
        "",
        "UKUPNO",
        "",
        "",
    ]
    programs = (
        [""] * 3 + ["REDOVITI PROGRAM", "POSEBNI PROGRAM"] * 4 + ["UKUPNO RED. + POS."]
    )
    programs += ["REDOVITI PROGRAM", "POSEBNI PROGRAM"] * 5 + ["UKUPNO RED. + POS."]
    values = ["Četvrt", "DV Primjer", "Druga četvrt"] + ["0"] * 20
    values[3], values[12] = "2", "3"
    for i in (9, 10, 11, 20, 21, 22):
        values[i] = "999"
    return [
        top,
        ages,
        programs,
        values,
        ["UKUPNO", "", ""] + ["999"] * 20,
        [FOOTER] + [""] * 22,
    ]


def childminder_table():
    return [
        [
            "Gradska četvrt",
            "GČ",
            "Naziv\nobrta za čuvanje djece (dadilje)",
            "Broj slobodnih mjesta\nod 1 godine do OŠ",
        ],
        ["Četvrt", "Četvrt", "DAD Primjer", "0"],
        ["UKUPNO", "", "", "0"],
        [FOOTER, "", "", ""],
    ]


def package(definition):
    d = definition.source
    return CkanPackage(
        id=d.dataset_id,
        name=d.dataset_id,
        title="Synthetic open snapshot",
        license_id="open-license",
        license_title="Otvorena dozvola (OD)",
        resources=[
            CkanResource(
                id=d.resource_id,
                url=f"https://example.invalid/{d.key}",
                format=d.resource_format,
                last_modified="2019-10-09T09:00:00"
                if d.parser == "programs"
                else "2025-01-02T09:00:00",
            )
        ],
    )
