"""Synthetic snapshots verify totals, date boundaries and atomic HTTP imports."""

import copy
import io
import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
from openpyxl import Workbook
from support.historical import (
    DEFINITIONS,
    FOOTER,
    PROGRAMS,
    childminder_table,
    historical_parser,
    historical_service,
    municipal_table,
    package,
)

from KIDSic.dto.ckan import CkanResource
from KIDSic.exceptions import CkanResponseError, SourceImportError
from KIDSic.integrations.concrete.ckan import CkanClient


class HistoricalParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = historical_parser()

    def test_programs_are_object_scoped_and_slash_is_unknown(self):
        rows = self.parser.parse(PROGRAMS, DEFINITIONS[0])
        self.assertEqual(rows[0].programs, ("Montessori", "engleski jezik"))
        self.assertEqual(rows[1].programs, ())
        self.assertEqual(rows[0].scope, "facility")
        self.assertNotEqual(rows[0].source_key, rows[1].source_key)

    def test_merged_headers_propagate_ages_without_duplicating_totals(self):
        (row,) = self.parser.parse(municipal_table(), DEFINITIONS[1])
        self.assertEqual(len(row.vacancies), 14)
        self.assertEqual(sum(v.free_places for v in row.vacancies), 5)
        self.assertEqual(row.vacancies[1].age_label, "od 1 do 2 godine")
        self.assertEqual(row.vacancies[1].free_places, 0)
        self.assertEqual((row.scope, row.address), ("institution", None))

    def test_missing_counts_remain_unknown_and_published_zero_is_preserved(self):
        table = municipal_table()
        table[3][4] = ""
        self.assertIsNone(
            self.parser.parse(table, DEFINITIONS[1])[0].vacancies[1].free_places
        )
        (row,) = self.parser.parse(childminder_table(), DEFINITIONS[2])
        self.assertEqual(row.vacancies[0].free_places, 0)
        self.assertEqual(row.vacancies[0].age_label, "od 1 godine do OŠ")

    def test_bad_headers_dates_counts_and_duplicate_identities_fail_closed(self):
        bad_tables = []
        for value in ("-1", "1.5", "nepoznato"):
            table = municipal_table()
            table[3][3] = value
            bad_tables.append((table, DEFINITIONS[1]))
        table = municipal_table()
        table[-1][0] = FOOTER.replace("2025", "2026")
        bad_tables.append((table, DEFINITIONS[1]))
        table = municipal_table()
        table[0] = table[0][:-1]
        bad_tables.append((table, DEFINITIONS[1]))
        bad_tables.append((PROGRAMS + [PROGRAMS[1]], DEFINITIONS[0]))
        table = copy.deepcopy(PROGRAMS)
        table[0][0] = "Renamed"
        bad_tables.append((table, DEFINITIONS[0]))
        for table, definition in bad_tables:
            with self.subTest(table=table), self.assertRaises(SourceImportError):
                self.parser.parse(table, definition)


class HistoricalServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_downloads_and_validation_finish_before_any_database_write(self):
        events = []
        clients = {
            d.source.key: SimpleNamespace(
                get_package=AsyncMock(return_value=package(d)),
                download_table=AsyncMock(return_value=table),
            )
            for d, table in zip(
                DEFINITIONS, (PROGRAMS, municipal_table(), childminder_table())
            )
        }

        @asynccontextmanager
        async def work():
            self.assertTrue(
                all(c.download_table.await_count == 1 for c in clients.values())
            )
            events.append("transaction")
            yield SimpleNamespace(
                sources=SimpleNamespace(register=AsyncMock()),
                historical=SimpleNamespace(
                    import_snapshot=AsyncMock(return_value={"records": 1})
                ),
            )

        result = await historical_service(clients, DEFINITIONS, work).import_data()
        self.assertEqual(result["records"], 3)
        self.assertEqual(events, ["transaction"])
        clients[DEFINITIONS[2].source.key].download_table.return_value = [["invalid"]]
        with self.assertRaises(SourceImportError):
            await historical_service(clients, DEFINITIONS, work).import_data()
        self.assertEqual(events, ["transaction"])

    async def test_changed_license_and_publication_date_require_review(self):
        definition = DEFINITIONS[0]
        for field, value in [("license_id", "unknown"), ("date", "2026-01-01")]:
            metadata = package(definition)
            if field == "date":
                metadata.resources[0].last_modified = value
            else:
                metadata.license_id = value
            client = SimpleNamespace(
                get_package=AsyncMock(return_value=metadata), download_table=AsyncMock()
            )
            with self.assertRaises(SourceImportError):
                await historical_service(
                    {definition.source.key: client}, [definition]
                ).preview_import()
            client.download_table.assert_not_awaited()

    async def test_http_table_reader_preserves_empty_headers_and_xlsx_cells(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["Name", None, "PROGRAMI"])
        sheet.append(["Čarobni", None, "Montessori"])
        buffer = io.BytesIO()
        workbook.save(buffer)
        workbook.close()
        for fmt, content, expected in [
            (
                "csv",
                b"Name;;PROGRAMI\r\nExample;;/\r\n",
                [["Name", "", "PROGRAMI"], ["Example", "", "/"]],
            ),
            (
                "text/csv",
                b"Name;;PROGRAMI\r\nExample;;/\r\n",
                [["Name", "", "PROGRAMI"], ["Example", "", "/"]],
            ),
            (
                "xlsx",
                buffer.getvalue(),
                [["Name", "", "PROGRAMI"], ["Čarobni", "", "Montessori"]],
            ),
            (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                buffer.getvalue(),
                [["Name", "", "PROGRAMI"], ["Čarobni", "", "Montessori"]],
            ),
        ]:
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(
                    lambda r, content=content: httpx.Response(200, content=content)
                )
            ) as http:
                resource = CkanResource(
                    id="synthetic", url="https://example.invalid/table", format=fmt
                )
                self.assertEqual(
                    await CkanClient(http).download_table(resource), expected
                )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, content=b"<html>bad</html>")
            )
        ) as http:
            with self.assertRaises(CkanResponseError):
                await CkanClient(http).download_table(
                    CkanResource(
                        id="bad", url="https://example.invalid/bad", format="xlsx"
                    )
                )
