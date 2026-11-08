"""Rijeka ingestion checks the published schema using synthetic addresses."""

import copy
import json
import unittest
from pathlib import Path

import httpx

from KIDSic.config.settings import Settings
from KIDSic.exceptions import SourceImportError
from KIDSic.factories.source import SourceServiceFactory
from KIDSic.services.concrete.kindergarten_normalizer import normalize_records

FIXTURES = Path(__file__).parent / "fixtures"


from support.rijeka import rijeka_records


class RijekaTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_ingestion_uses_primary_catalogue_pinned_csv_and_windows_encoding(
        self,
    ):
        package = json.loads((FIXTURES / "ckan_rijeka.json").read_text())
        package["result"]["resources"].append(
            {
                "id": "unrelated-csv",
                "url": "https://example.invalid/unrelated.csv",
                "format": "CSV",
            }
        )
        requests = []

        def respond(request):
            requests.append(request)
            if request.url.path.endswith("package_show"):
                return httpx.Response(200, json=package)
            return httpx.Response(
                200, content=(FIXTURES / "rijeka.csv").read_text().encode("cp1250")
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
            service = SourceServiceFactory(
                Settings(database_url="postgresql://localhost/unused")
            ).create(http, source_keys=["rijeka-kindergartens"])
            preview = await service.preview_import()
            self.assertFalse(http.is_closed)
        self.assertEqual(preview["sources"][0]["records"], 8)
        self.assertEqual(
            str(requests[0].url),
            "https://data.rijeka.hr/api/3/action/package_show?id=djecji-vrtici",
        )
        self.assertEqual(str(requests[1].url), "https://example.invalid/rijeka.csv")
        rows = normalize_records(rijeka_records(), "rijeka-kindergartens")
        self.assertTrue(rows[2].location_name.endswith("Oblačić"))
        self.assertEqual(rows[2].name, "Dječji vrtić Rijeka")
        self.assertEqual(rows[3].name, rows[0].name)
        self.assertEqual(rows[3].raw_data["Centar"], "KBC Rijeka")
        self.assertIn("waldorfski", rows[4].name)
        self.assertEqual(
            [r.provider_kind for r in rows],
            ["municipal"] * 4 + ["private", "religious", "religious", "private"],
        )
        self.assertEqual({r.municipality for r in rows}, {"rijeka"})
        self.assertEqual({r.scope for r in rows}, {"location"})
        self.assertTrue(
            all(
                r.longitude is None and r.latitude is None and r.phone is None
                for r in rows
            )
        )

    async def test_changed_resource_and_license_are_rejected_before_download(self):
        original = json.loads((FIXTURES / "ckan_rijeka.json").read_text())
        for change in (
            {"id": "replacement"},
            {"format": "XLSX"},
            {"state": "deleted"},
            {"license_id": "open-license"},
            {"license_id": None},
        ):
            package = copy.deepcopy(original)
            if "license_id" in change:
                package["result"].update(change)
            else:
                package["result"]["resources"][0].update(change)
            requests = []

            def respond(request, requests=requests, package=package):
                requests.append(request)
                return httpx.Response(200, json=package)

            async with httpx.AsyncClient(
                transport=httpx.MockTransport(respond)
            ) as http:
                service = SourceServiceFactory(
                    Settings(database_url="postgresql://localhost/unused")
                ).create(http, source_keys=["rijeka-kindergartens"])
                with self.subTest(change=change), self.assertRaises(SourceImportError):
                    await service.preview_import()
                self.assertEqual(len(requests), 1)

    async def test_unknown_founders_are_not_guessed_and_row_order_is_not_identity(self):
        original = rijeka_records()[0]
        row = normalize_records([original], "rijeka-kindergartens")[0]
        changed = normalize_records(
            [
                {
                    **original,
                    "RBR": "90",
                    "Adresa": "Nova 99",
                    "Adresa centra": "Drugo sjedište",
                }
            ],
            "rijeka-kindergartens",
        )[0]
        self.assertEqual(row.source_key, changed.source_key)
        unknown = normalize_records(
            [{**original, "Osnivač": "Novi nepoznati osnivač"}], "rijeka-kindergartens"
        )[0]
        self.assertEqual(unknown.provider_kind, "unknown")
        self.assertIsNone(unknown.provider_kind_source_url)
        for changes in (
            {"RBR": "0"},
            {"RBR": "NaN"},
            {"Adresa": ""},
            {"Centar": ""},
            {"Osnivač": ""},
            {"Vrtić": "Drugi", "Centar": "KBC Rijeka"},
        ):
            with self.subTest(changes=changes), self.assertRaises(SourceImportError):
                normalize_records([{**original, **changes}], "rijeka-kindergartens")
        with self.assertRaises(SourceImportError):
            normalize_records(
                [original, {**original, "RBR": "2"}], "rijeka-kindergartens"
            )
