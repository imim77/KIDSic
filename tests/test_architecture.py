"""Architecture tests protect dependency direction and replaceable business policies."""

import ast
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from support.sources import source_client, source_service

from KIDSic.dto.source import KindergartenRow, SourceDefinition
from KIDSic.services.concrete.source_normalizer import SourceRecordNormalizer
from KIDSic.services.interfaces.source_parser import SourceRowParser

ROOT = Path(__file__).resolve().parents[1] / "src" / "KIDSic"


def imported_modules(path):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module:
            yield node.module
        elif isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)


class LayerDependencyTests(unittest.TestCase):
    def test_business_and_contracts_do_not_import_infrastructure_implementations(self):
        paths = [
            *ROOT.joinpath("services/concrete").rglob("*.py"),
            *ROOT.joinpath("services/interfaces").rglob("*.py"),
            *ROOT.joinpath("dao/interfaces").rglob("*.py"),
            ROOT / "db/uow/base.py",
            ROOT / "db/uow/source.py",
        ]
        forbidden = (
            "asyncpg",
            "httpx",
            "sqlalchemy",
            "starlette",
            "mcp",
            "KIDSic.dao.concrete",
            "KIDSic.integrations.concrete",
            "KIDSic.factories",
        )
        self.assert_no_imports(paths, forbidden)

    def test_persistence_never_calls_presentation_or_business_services(self):
        self.assert_no_imports(
            ROOT.joinpath("dao").rglob("*.py"),
            ("KIDSic.api", "KIDSic.services", "KIDSic.factories"),
        )

    def test_presentation_uses_services_without_database_drivers(self):
        paths = [
            path
            for package in ("api", "commands")
            for path in ROOT.joinpath(package).rglob("*.py")
        ]
        self.assert_no_imports(
            paths, ("asyncpg", "sqlalchemy", "KIDSic.dao", "KIDSic.db")
        )

    def test_services_and_presentation_depend_on_service_interfaces(self):

        paths = [
            path
            for path in (
                *ROOT.joinpath("services/concrete").glob("*.py"),
                *ROOT.joinpath("api").rglob("*.py"),
            )
            if path.name != "kindergarten_normalizer.py"
        ]
        self.assert_no_imports(paths, ("KIDSic.services.concrete",))

    def assert_no_imports(self, paths, forbidden):
        for path in paths:
            for module in imported_modules(path):
                with self.subTest(path=path.relative_to(ROOT), module=module):
                    self.assertFalse(
                        any(
                            module == name or module.startswith(name + ".")
                            for name in forbidden
                        ),
                        f"{path.relative_to(ROOT)} imports {module}",
                    )

    def test_legacy_mcp_entry_point_still_uses_the_same_application(self):
        from KIDSic.api.mcp_server import create_app
        from KIDSic.mcp.server import create_app as legacy

        self.assertIs(legacy, create_app)


class ExtensibleSourceTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_new_schema_can_be_injected_without_changing_service_or_normalizer(
        self,
    ):
        class ExampleParser(SourceRowParser):
            def parse(self, record):
                return KindergartenRow(
                    source_key=record["id"],
                    raw_data=record,
                    name="Example",
                    location_name="Example",
                    settlement="Varaždin",
                    address="Example 1",
                    municipality="varazdin",
                )

        client = source_client()
        client.download_records = AsyncMock(return_value=[{"id": "one"}, {"id": "two"}])
        definition = SourceDefinition(
            "example", "https://data.gov.hr/ckan", "example", "custom-schema"
        )
        service = source_service(
            {"example": client},
            [definition],
            normalizer=SourceRecordNormalizer({"custom-schema": ExampleParser()}),
        )
        result = await service.preview_import()
        self.assertEqual(result["sources"][0]["records"], 2)
