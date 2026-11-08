"""Actual asyncpg persistence and transaction tests on a disposable migrated database."""

import json
import os
import unittest
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import httpx
from legacy_schema import current_table_names
from support.database import DatabaseTestCase
from support.sources import MUNICIPAL, NATIONAL, source_client, source_service

from KIDSic.config.settings import Settings
from KIDSic.dao.concrete.asyncpg_location import AsyncpgLocationRepository
from KIDSic.dao.concrete.asyncpg_source import AsyncpgSourceRepository
from KIDSic.db.uow.asyncpg_source import AsyncpgSourceUnitOfWork
from KIDSic.dto.location import LocationQuery
from KIDSic.dto.source import PlannedSource, SourceDefinition, SourceSnapshot
from KIDSic.exceptions import PersistenceError, SourceImportError
from KIDSic.factories.source import SourceServiceFactory
from KIDSic.services.concrete.kindergarten_normalizer import normalize_records


class SourceDatabaseTests(DatabaseTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.repo = AsyncpgSourceRepository(self.connection)
        self.client = source_client()
        self.definition = SourceDefinition(
            "national", "https://data.gov.hr/ckan", "djecji-vrtici", "national"
        )
        self.source = PlannedSource(
            self.definition,
            self.client.get_package.return_value,
            self.client.get_package.return_value.resources[0],
        )

    def snapshot(self, records=None, source=None, parser="national"):
        return SourceSnapshot(
            source or self.source,
            normalize_records(records or [NATIONAL], parser),
            datetime.now(UTC),
        )

    async def test_city_scope_filters_reimports_and_rejects_unfiltered_snapshots(self):
        from dataclasses import replace

        records = [
            {**NATIONAL, "Mjesto": city, "Zupanija": county}
            for city, county in (
                ("Zagreb", "Grad Zagreb"),
                ("Varaždin", "Varaždinska županija"),
                ("Rijeka", "Primorsko-goranska županija"),
                ("Split", "Splitsko-dalmatinska županija"),
            )
        ]
        snapshot = self.snapshot(records)
        await self.repo.import_snapshot(snapshot)
        identities = await self.connection.fetch(
            "SELECT k.id,ks.naselje AS seat_settlement FROM vrtici k LEFT JOIN sjedista_vrtica ks ON ks.id_vrtica=k.id ORDER BY k.id"
        )
        self.assertEqual(
            {r["seat_settlement"] for r in identities}, {"Zagreb", "Varaždin", "Rijeka"}
        )
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM izvorni_zapisi"), 3
        )
        await self.repo.import_snapshot(self.snapshot(records))
        self.assertEqual(
            await self.connection.fetch(
                "SELECT k.id,ks.naselje AS seat_settlement FROM vrtici k LEFT JOIN sjedista_vrtica ks ON ks.id_vrtica=k.id ORDER BY k.id"
            ),
            identities,
        )
        bad = replace(snapshot, rows=(replace(snapshot.rows[0], municipality="split"),))
        with self.assertRaises(SourceImportError):
            await self.repo.import_snapshot(bad)
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM izvorni_zapisi"), 3
        )

    async def test_city_cleanup_preserves_supported_branches_and_removes_dependent_data(
        self,
    ):
        await self.connection.execute(
            "ALTER TABLE vrtici ADD COLUMN seat_settlement text, ADD COLUMN seat_settlement_key text, ADD COLUMN seat_municipality_id uuid REFERENCES jedinice_lokalne_samouprave(id)"
        )
        legacy = (
            Path(__file__).resolve().parents[1]
            / "src/KIDSic/db/alembic/versions/0001_simple_rag.sql"
        ).read_text()
        for sql in legacy.split("\n-- statement\n"):
            if sql.startswith(("CREATE TABLE program", "CREATE INDEX ix_program")):
                await self.connection.execute(current_table_names(sql))
        await self.connection.execute(
            "ALTER TABLE odlomci_znanja ADD COLUMN program_id uuid"
        )
        await self.connection.execute(
            "ALTER TABLE upisni_krugovi ADD COLUMN id_jedinice_lokalne_samouprave uuid REFERENCES jedinice_lokalne_samouprave(id)"
        )
        await self.repo.register(self.source)
        source_id = await self.connection.fetchval(
            "SELECT id FROM izvori_podataka WHERE kljuc_skupa_podataka='national'"
        )
        cities = {
            city: await self.connection.fetchval(
                "INSERT INTO jedinice_lokalne_samouprave(kljuc,naziv) VALUES ($1,$1) RETURNING id",
                city,
            )
            for city in ("zagreb", "varazdin", "rijeka", "split", "osijek")
        }

        async def place(name, city, *, owner=None, settlement=None):
            if owner is None:
                owner = await self.connection.fetchval(
                    """INSERT INTO vrtici
                    (naziv,seat_settlement,seat_settlement_key,seat_municipality_id)
                    VALUES ($1,$2,$2,$3) RETURNING id""",
                    name,
                    city,
                    cities[city],
                )
            location = await self.connection.fetchval(
                """INSERT INTO objekti
                (id_vrtica,naziv,naselje,kljuc_naselja,id_jedinice_lokalne_samouprave)
                VALUES ($1,$2,$3,$3,$4) RETURNING id""",
                owner,
                name,
                settlement or city,
                cities[city],
            )
            record = await self.connection.fetchval(
                """INSERT INTO izvorni_zapisi
                (id_izvora,izvorni_podaci,id_vrtica,id_objekta,status_povezivanja,metoda_povezivanja)
                VALUES ($1,'{}',$2,$3,'accepted','manual') RETURNING id""",
                source_id,
                owner,
                location,
            )
            program = await self.connection.fetchval(
                """INSERT INTO program
                (id_vrtica,id_objekta,id_izvornog_zapisa,naziv,datum_provjere)
                VALUES ($1,$2,$3,'Synthetic',CURRENT_DATE) RETURNING id""",
                owner,
                location,
                record,
            )
            await self.connection.execute(
                """INSERT INTO upisni_krugovi
                (id_vrtica,id_izvornog_zapisa,pedagoska_godina,poveznica_za_prijavu,kanal_prijave)
                VALUES ($1,$2,'2026/27','https://example.invalid','kindergarten')""",
                owner,
                record,
            )
            await self.connection.execute(
                """INSERT INTO odlomci_znanja
                (id_vrtica,id_objekta,id_izvornog_zapisa,program_id,redni_broj,sadrzaj,poveznica_izvora)
                VALUES ($1,$2,$3,$4,0,'Synthetic','https://example.invalid')""",
                owner,
                location,
                record,
                program,
            )
            return owner, location, record

        await place("Outside only", "split")
        rijeka = await place("Rijeka retained", "rijeka")
        external = await place("External seat", "split")
        zagreb = await place(
            "Zagreb branch", "zagreb", owner=external[0], settlement="sesvete"
        )
        varazdin = await place("Varaždin retained", "varazdin")
        for city, county in (
            ("Split", "Splitsko-dalmatinska županija"),
            ("Sesvete", "Grad Zagreb"),
        ):
            await self.connection.execute(
                """INSERT INTO izvorni_zapisi(id_izvora,izvorni_podaci)
                VALUES ($1,$2)""",
                source_id,
                {**NATIONAL, "Mjesto": city, "Zupanija": county},
            )
        await self.connection.execute(
            """INSERT INTO upisni_krugovi
            (id_jedinice_lokalne_samouprave,id_izvornog_zapisa,pedagoska_godina,poveznica_za_prijavu,kanal_prijave)
            VALUES ($1,$2,'2026/27','https://example.invalid','city_system')""",
            cities["split"],
            rijeka[2],
        )

        await self.connection.execute(
            "CREATE TEMP TABLE availability (id_izvornog_zapisa uuid, id_vrtica uuid, id_objekta uuid, program_id uuid)"
        )
        migration = (
            Path(__file__).resolve().parents[1]
            / "src/KIDSic/db/alembic/versions/0005_supported_cities.sql"
        ).read_text()
        await self.connection.execute(current_table_names(migration))
        self.assertEqual(
            {r["id"] for r in await self.connection.fetch("SELECT id FROM vrtici")},
            {rijeka[0], external[0], varazdin[0]},
        )
        self.assertEqual(
            {r["id"] for r in await self.connection.fetch("SELECT id FROM objekti")},
            {rijeka[1], zagreb[1], varazdin[1]},
        )
        for table in ("program", "upisni_krugovi", "odlomci_znanja"):
            self.assertEqual(
                await self.connection.fetchval(f"SELECT count(*) FROM {table}"),
                3,
                table,
            )
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM izvorni_zapisi"), 4
        )
        self.assertIsNone(
            await self.connection.fetchval(
                "SELECT id FROM jedinice_lokalne_samouprave WHERE kljuc='osijek'"
            )
        )
        await self.connection.execute(current_table_names(migration))
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM vrtici"), 3
        )

    async def test_provider_types_survive_reimport_and_are_exposed_with_their_source(
        self,
    ):
        from KIDSic.dao.concrete.asyncpg_location import AsyncpgLocationRepository
        from KIDSic.dto.location import LocationQuery

        records = [
            {**NATIONAL, "Naziv": name}
            for name in ("DV Varaždin", "DV Bajka", "DV Sveta Uršula")
        ]
        await self.repo.import_snapshot(self.snapshot(records))
        identities = await self.connection.fetch(
            "SELECT id,vrsta_pruzatelja  AS provider_kind FROM vrtici ORDER BY naziv"
        )
        await self.repo.import_snapshot(self.snapshot(records))
        self.assertEqual(
            await self.connection.fetch(
                "SELECT id,vrsta_pruzatelja  AS provider_kind FROM vrtici ORDER BY naziv"
            ),
            identities,
        )
        locations = AsyncpgLocationRepository(self.connection)
        for kind in ("municipal", "private", "religious"):
            rows = await locations.list_locations(
                LocationQuery(city="Varaždin", provider_kind=kind)
            )
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["provider_kind"], kind)
            self.assertIn("provider_kind", rows[0]["field_sources"])
            self.assertEqual(
                await self.connection.fetchval(
                    "SELECT podrijetlo->'provider_kind'->>'source_url' FROM vrtici WHERE id=$1",
                    rows[0]["kindergarten_id"],
                ),
                "https://varazdin.hr/djecji-vrtici/",
            )
        options = await AsyncpgLocationRepository(self.connection).list_locations(
            LocationQuery(city="varazdin")
        )
        self.assertEqual(
            {row["provider_kind"] for row in options},
            {"municipal", "private", "religious"},
        )

    async def test_provider_backfill_preserves_known_types_and_other_cities(self):
        records = [
            {**NATIONAL, "Naziv": "DV Bajka"},
            {**NATIONAL, "Naziv": "DV Varaždin"},
            {
                **NATIONAL,
                "Naziv": "Udruga Primjer",
                "Mjesto": "Zagreb",
                "Zupanija": "Grad Zagreb",
            },
        ]
        await self.repo.import_snapshot(self.snapshot(records))
        await self.connection.execute(
            "ALTER TABLE vrtici ADD COLUMN seat_settlement text, ADD COLUMN seat_settlement_key text, ADD COLUMN seat_municipality_id uuid, ADD COLUMN seat_county text"
        )
        await self.connection.execute(
            "UPDATE vrtici k SET seat_settlement=ks.naselje,seat_settlement_key=ks.kljuc_naselja,seat_municipality_id=ks.id_jedinice_lokalne_samouprave,seat_county=m.zupanija FROM sjedista_vrtica ks LEFT JOIN jedinice_lokalne_samouprave m ON m.id=ks.id_jedinice_lokalne_samouprave WHERE k.id=ks.id_vrtica"
        )
        # Simulate a legacy row without passing through the now city-limited import.
        await self.connection.execute(
            "INSERT INTO vrtici(naziv,seat_settlement,seat_settlement_key) VALUES ('DV Bajka','Drugi grad','drugi grad')"
        )
        await self.connection.execute("UPDATE vrtici SET vrsta_pruzatelja='unknown'")
        await self.connection.execute(
            "UPDATE vrtici SET vrsta_pruzatelja='private' WHERE naziv='DV Varaždin'"
        )
        before = await self.connection.fetch(
            "SELECT id,naziv AS name,seat_settlement,vrsta_pruzatelja AS provider_kind,podrijetlo  AS provenance FROM vrtici ORDER BY id"
        )
        migration = (
            Path(__file__).resolve().parents[1] / "src/KIDSic/db/alembic/versions/"
            "0004_provider_kinds.sql"
        ).read_text()
        await self.connection.execute(current_table_names(migration))
        rows = await self.connection.fetch(
            "SELECT id,naziv AS name,seat_settlement,vrsta_pruzatelja AS provider_kind,podrijetlo  AS provenance FROM vrtici ORDER BY id"
        )
        self.assertEqual(
            {(r["name"], r["seat_settlement"]): r["provider_kind"] for r in rows},
            {
                ("DV Bajka", "Varaždin"): "private",
                ("DV Varaždin", "Varaždin"): "private",
                ("DV Bajka", "Drugi grad"): "unknown",
                ("Udruga Primjer", "Zagreb"): "other",
            },
        )
        await self.connection.execute(current_table_names(migration))
        self.assertEqual(
            await self.connection.fetch(
                "SELECT id,naziv AS name,seat_settlement,vrsta_pruzatelja AS provider_kind,podrijetlo  AS provenance FROM vrtici ORDER BY id"
            ),
            rows,
        )
        import importlib.util
        from unittest.mock import patch

        spec = importlib.util.spec_from_file_location(
            "provider_migration",
            Path(__file__).resolve().parents[1] / "src/KIDSic/db/alembic/versions/"
            "0004_provider_kinds.py",
        )
        revision = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(revision)
        with patch.object(revision.op, "execute") as execute:
            revision.downgrade()
        await self.connection.execute(current_table_names(execute.call_args.args[0]))
        self.assertEqual(
            await self.connection.fetch(
                "SELECT id,naziv AS name,seat_settlement,vrsta_pruzatelja AS provider_kind,podrijetlo  AS provenance FROM vrtici ORDER BY id"
            ),
            before,
        )

    async def test_database_rejects_missing_or_invalid_provider_kind(self):
        import asyncpg

        for kind, error in (
            (None, asyncpg.NotNullViolationError),
            ("invalid", asyncpg.CheckViolationError),
        ):
            with self.subTest(kind=kind), self.assertRaises(error):
                async with self.connection.transaction():
                    await self.connection.execute(
                        "INSERT INTO vrtici(naziv,vrsta_pruzatelja) VALUES ('Synthetic',$1)",
                        kind,
                    )

    async def test_childminder_csv_import_preserves_identity_and_last_good_snapshot(
        self,
    ):
        fixtures = Path(__file__).parent / "fixtures"
        package = json.loads((fixtures / "ckan_childminders.json").read_text())
        state = {"bad": False, "moved": False}

        def respond(request):
            if request.url.path.endswith("package_show"):
                return httpx.Response(200, json=package)
            body = (fixtures / "varazdin_childminders.csv").read_bytes()
            if state["bad"]:
                body = b"wrong;columns\n1;2"
            elif state["moved"]:
                body = body.replace(b"Primjer 1,", b"Primjer 99,")
            return httpx.Response(200, content=body)

        @asynccontextmanager
        async def work():
            async with self.connection.transaction():
                yield SimpleNamespace(sources=self.repo)

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
            service = SourceServiceFactory(
                Settings(database_url=os.environ["KIDSIC_TEST_DATABASE_URL"])
            ).create(http, work, source_keys=["varazdin-childminders"])
            first = await service.import_data()
            self.assertEqual(first["records"], 2)
            self.assertEqual(first["sources"][0]["accepted"], 2)
            identities = await self.connection.fetch(
                "SELECT id,oib FROM vrtici ORDER BY naziv"
            )
            state["moved"] = True
            second = await service.import_data()
            self.assertEqual(second["sources"][0]["kindergartens_added"], 0)
            self.assertEqual(
                await self.connection.fetch("SELECT id,oib FROM vrtici ORDER BY naziv"),
                identities,
            )
            self.assertEqual(
                await self.connection.fetchval("SELECT count(*) FROM objekti"), 0
            )
            self.assertEqual(
                await self.connection.fetchval("SELECT count(*) FROM odlomci_znanja"), 0
            )
            self.assertEqual(
                await self.connection.fetchval(
                    "SELECT count(*) FROM vrtici WHERE vrsta_pruzatelja='childminder'"
                ),
                2,
            )
            self.assertEqual(
                await self.connection.fetchval(
                    "SELECT ks.adresa  AS address FROM vrtici k JOIN sjedista_vrtica ks ON ks.id_vrtica=k.id WHERE k.oib='00123456789'"
                ),
                "Primjer 99",
            )
            rows = await AsyncpgLocationRepository(self.connection).list_locations(
                LocationQuery(city="varazdin")
            )
            self.assertEqual({row["location_role"] for row in rows}, {"seat"})
            before = await self.connection.fetchval(
                "SELECT dohvaceno_u  AS fetched_at FROM izvori_podataka WHERE kljuc_skupa_podataka='varazdin-childminders'"
            )
            state["bad"] = True
            with self.assertRaises(SourceImportError):
                await service.import_data()
            self.assertEqual(
                await self.connection.fetchval(
                    "SELECT dohvaceno_u  AS fetched_at FROM izvori_podataka WHERE kljuc_skupa_podataka='varazdin-childminders'"
                ),
                before,
            )
            self.assertEqual(
                await self.connection.fetchval("SELECT count(*) FROM izvorni_zapisi"), 2
            )

    async def test_registration_is_idempotent_and_preserves_approval_and_fetch_time(
        self,
    ):
        self.assertEqual(await self.repo.register(self.source), "added")
        self.assertEqual(await self.repo.register(self.source), "unchanged")
        await self.repo.import_snapshot(self.snapshot())
        await self.connection.execute(
            "UPDATE izvori_podataka SET uvoz_dopusten=false WHERE kljuc_skupa_podataka='national'"
        )
        before = dict(
            await self.connection.fetchrow(
                "SELECT id,kljuc_skupa_podataka AS dataset_key,naslov AS title,izdavac AS publisher,poveznica AS url,licenca AS license,uvoz_dopusten AS import_allowed,dohvaceno_u AS fetched_at,datum_opazanja AS observed_on,metapodaci AS metadata,vrsta AS kind FROM izvori_podataka WHERE kljuc_skupa_podataka='national'"
            )
        )
        changed = PlannedSource(
            self.definition,
            self.source.package.model_copy(update={"title": "New title"}),
            self.source.resource,
        )
        self.assertEqual(await self.repo.register(changed), "updated")
        after = await self.connection.fetchrow(
            "SELECT id,kljuc_skupa_podataka AS dataset_key,naslov AS title,izdavac AS publisher,poveznica AS url,licenca AS license,uvoz_dopusten AS import_allowed,dohvaceno_u AS fetched_at,datum_opazanja AS observed_on,metapodaci AS metadata,vrsta AS kind FROM izvori_podataka WHERE kljuc_skupa_podataka='national'"
        )
        for key in ("import_allowed", "fetched_at"):
            self.assertEqual(after[key], before[key])
        with self.assertRaises(SourceImportError):
            await self.repo.import_snapshot(self.snapshot())

    async def test_resource_identity_and_url_cannot_be_registered_under_another_source(
        self,
    ):
        await self.repo.register(self.source)
        other_definition = SourceDefinition(
            "other-key",
            self.definition.base_url,
            self.definition.dataset_id,
            "national",
        )
        duplicate = PlannedSource(
            other_definition, self.source.package, self.source.resource
        )
        with self.assertRaises(SourceImportError):
            await self.repo.register(duplicate)
        changed_id = PlannedSource(
            other_definition,
            self.source.package,
            self.source.resource.model_copy(update={"id": "replacement-id"}),
        )
        with self.assertRaises(SourceImportError):
            await self.repo.register(changed_id)
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM izvori_podataka"), 1
        )

    async def test_repeated_import_preserves_ids_raw_evidence_and_unknown_age(self):
        first = await self.repo.import_snapshot(self.snapshot())
        identity = await self.connection.fetchval("SELECT id FROM vrtici")
        record_identity = await self.connection.fetchval(
            "SELECT id FROM izvorni_zapisi"
        )
        second = await self.repo.import_snapshot(
            self.snapshot([{**NATIONAL, "Telefon": "123"}])
        )
        # The national directory describes institutions: its address is a seat, not an object.
        self.assertEqual((first["locations_added"], second["locations_added"]), (0, 0))
        self.assertEqual(second["kindergartens_added"], 0)
        self.assertEqual(
            await self.connection.fetchval("SELECT id FROM izvorni_zapisi"),
            record_identity,
        )
        self.assertEqual(
            await self.connection.fetchval("SELECT id FROM vrtici"), identity
        )
        seat = await self.connection.fetchrow(
            "SELECT ks.adresa AS address,ks.naselje AS settlement,ks.postanski_broj AS postal_code,m.kljuc  AS key FROM vrtici k JOIN sjedista_vrtica ks ON ks.id_vrtica=k.id JOIN jedinice_lokalne_samouprave m ON m.id=ks.id_jedinice_lokalne_samouprave"
        )
        self.assertEqual(tuple(seat), ("Primjer 1", "Varaždin", "42000", "varazdin"))
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM objekti"), 0
        )
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM izvorni_zapisi"), 1
        )
        self.assertEqual(
            [
                r["match_method"]
                for r in await self.connection.fetch(
                    "SELECT metoda_povezivanja  AS match_method FROM izvorni_zapisi ORDER BY dohvaceno_u"
                )
            ],
            ["new"],
        )
        self.assertEqual(
            await self.connection.fetchval("SELECT telefon  AS phone FROM vrtici"),
            "123",
        )
        raw = await self.connection.fetchval(
            "SELECT izvorni_podaci  AS raw_data FROM izvorni_zapisi WHERE id=$1",
            record_identity,
        )
        self.assertEqual(raw["Telefon"], "123")
        search = AsyncpgLocationRepository(self.connection)
        result = await search.list_locations(LocationQuery(city="varazdina"))
        self.assertEqual(result[0]["location_role"], "seat")
        self.assertIsNone(
            await self.connection.fetchval(
                "SELECT datum_opazanja  AS observed_on FROM izvori_podataka"
            )
        )

    def municipal_source(self):
        client = source_client("municipal")
        return PlannedSource(
            SourceDefinition(
                "zagreb-municipal",
                "https://data.zagreb.hr",
                "gradski_vrtici_grada_zagreba",
                "municipal",
            ),
            client.get_package.return_value,
            client.get_package.return_value.resources[0],
        )

    async def test_city_objects_share_owner_and_link_to_national_record(self):
        await self.repo.import_snapshot(
            self.snapshot([{**NATIONAL, "Mjesto": "Zagreb", "Zupanija": "Grad Zagreb"}])
        )
        branch = {
            **MUNICIPAL,
            "Id": 2,
            "Naziv": "DV Primjer-PO Druga",
            "Adresa": "Druga 2",
            "TipVrtica": "Područni",
        }
        await self.repo.import_snapshot(
            self.snapshot([MUNICIPAL, branch], self.municipal_source(), "municipal")
        )
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM vrtici"), 1
        )
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM objekti"), 2
        )
        self.assertEqual(
            await self.connection.fetchval(
                "SELECT count(DISTINCT id_izvora) FROM izvorni_zapisi"
            ),
            2,
        )
        self.assertEqual(
            await self.connection.fetchval(
                "SELECT count(*) FROM objekti WHERE vrsta='branch'"
            ),
            1,
        )
        self.assertEqual(
            [
                r["match_method"]
                for r in await self.connection.fetch(
                    "SELECT metoda_povezivanja  AS match_method FROM izvorni_zapisi WHERE id_objekta IS NOT NULL ORDER BY kljuc_izvornog_zapisa"
                )
            ],
            ["name", "name"],
        )
        rows = await AsyncpgLocationRepository(self.connection).list_locations(
            LocationQuery(city="zagreb")
        )
        self.assertEqual({r["location_role"] for r in rows}, {"facility"})

    async def test_rijeka_csv_links_national_parents_preserves_contacts_and_reimports(
        self,
    ):
        from support.rijeka import rijeka_records, rijeka_source

        from KIDSic.dao.concrete.asyncpg_location import AsyncpgLocationRepository
        from KIDSic.dto.location import LocationQuery

        records = rijeka_records()
        parents = [
            "Dječji vrtić Rijeka",
            'Dječji vrtić "Mala Vila", waldorfski',
            'Dječji vrtić "Nazaret"',
            'Dječji vrtić "Pinokio"',
        ]
        national = [
            {
                **NATIONAL,
                "Naziv": name,
                "Mjesto": "Rijeka",
                "Zupanija": "Primorsko-goranska županija",
                "Adresa": f"Sjedište {i}",
                "Telefon": "051/000001",
                "ePosta": "test@example.invalid",
            }
            for i, name in enumerate(parents)
        ]
        await self.repo.import_snapshot(self.snapshot(national))
        owners = await self.connection.fetch(
            "SELECT k.id,k.naziv AS name,ks.adresa AS seat_address FROM vrtici k LEFT JOIN sjedista_vrtica ks ON ks.id_vrtica=k.id ORDER BY k.id"
        )
        source = rijeka_source()
        first = await self.repo.import_snapshot(
            self.snapshot(records, source, "rijeka-kindergartens")
        )
        self.assertEqual(
            (first["accepted"], first["kindergartens_added"], first["locations_added"]),
            (8, 0, 8),
        )
        self.assertEqual(
            await self.connection.fetch(
                "SELECT k.id,k.naziv AS name,ks.adresa AS seat_address FROM vrtici k LEFT JOIN sjedista_vrtica ks ON ks.id_vrtica=k.id ORDER BY k.id"
            ),
            owners,
        )
        locations = await self.connection.fetch(
            "SELECT id,id_vrtica  AS kindergarten_id FROM objekti ORDER BY id"
        )
        api = await AsyncpgLocationRepository(self.connection).list_locations(
            LocationQuery(city="Rijeka")
        )
        self.assertEqual(len(api), 8)
        self.assertEqual({r["phone"] for r in api}, {"051/000001"})
        self.assertEqual({r["location_role"] for r in api}, {"facility"})
        self.assertTrue(
            all(r["longitude"] is None and r["latitude"] is None for r in api)
        )
        self.assertEqual(
            {r["provider_kind"] for r in api}, {"municipal", "private", "religious"}
        )
        self.assertTrue(
            all(r["sources"] and r["field_sources"].get("address") for r in api)
        )
        changed = [{**r, "RBR": str(i + 100)} for i, r in enumerate(reversed(records))]
        changed[-1]["Adresa"] = "Nova adresa 99"
        second = await self.repo.import_snapshot(
            self.snapshot(changed, source, "rijeka-kindergartens")
        )
        self.assertEqual(
            (second["kindergartens_added"], second["locations_added"]), (0, 0)
        )
        self.assertEqual(
            await self.connection.fetch(
                "SELECT id,id_vrtica  AS kindergarten_id FROM objekti ORDER BY id"
            ),
            locations,
        )
        self.assertEqual(
            await self.connection.fetchval(
                "SELECT count(*) FROM objekti WHERE adresa='Nova adresa 99'"
            ),
            1,
        )
        # The national refresh must preserve the facility category and parent identity.
        await self.repo.import_snapshot(self.snapshot(national))
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM vrtici"), 4
        )
        self.assertEqual(
            await self.connection.fetchval(
                "SELECT count(*) FROM vrtici WHERE vrsta_pruzatelja='unknown'"
            ),
            0,
        )
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM izvorni_zapisi"), 12
        )

    async def test_rijeka_csv_can_precede_national_import_without_duplicate_parents(
        self,
    ):
        from support.rijeka import rijeka_records, rijeka_source

        records = rijeka_records()
        await self.repo.import_snapshot(
            self.snapshot(records, rijeka_source(), "rijeka-kindergartens")
        )
        owners = await self.connection.fetch("SELECT id FROM vrtici ORDER BY id")
        self.assertEqual(len(owners), 4)
        national = [
            {
                **NATIONAL,
                "Naziv": name,
                "Mjesto": "Rijeka",
                "Zupanija": "Primorsko-goranska županija",
            }
            for name in (
                "Dječji vrtić Rijeka",
                'Dječji vrtić "Mala Vila", waldorfski',
                "Dječji vrtić Nazaret",
                "Dječji vrtić Pinokio",
            )
        ]
        result = await self.repo.import_snapshot(self.snapshot(national))
        self.assertEqual(result["kindergartens_added"], 0)
        self.assertEqual(
            await self.connection.fetch("SELECT id FROM vrtici ORDER BY id"), owners
        )
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM objekti"), 8
        )

    async def test_zagreb_settlement_suffix_links_to_national_settlement(self):
        await self.repo.import_snapshot(
            self.snapshot(
                [
                    {
                        **NATIONAL,
                        "Mjesto": "Sesvete",
                        "Adresa": "Sjedište 3",
                        "Zupanija": "Grad Zagreb",
                    }
                ]
            )
        )
        main = {**MUNICIPAL, "Adresa": "Ive Tijardovića 9, Sesvete"}
        await self.repo.import_snapshot(
            self.snapshot([main], self.municipal_source(), "municipal")
        )
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM vrtici"), 1
        )
        location = await self.connection.fetchrow(
            "SELECT naselje AS settlement,adresa AS address,m.kljuc  AS key FROM objekti l JOIN jedinice_lokalne_samouprave m ON m.id=l.id_jedinice_lokalne_samouprave"
        )
        self.assertEqual(tuple(location), ("Sesvete", "Ive Tijardovića 9", "zagreb"))
        search = AsyncpgLocationRepository(self.connection)
        for city in ("zagreba",):
            self.assertEqual(
                len(await search.list_locations(LocationQuery(city=city))), 1
            )

    async def test_oib_links_institution_despite_different_name(self):
        from dataclasses import replace

        rows = normalize_records([NATIONAL], "national")
        await self.repo.import_snapshot(
            SourceSnapshot(
                self.source,
                (replace(rows[0], oib="12345678901"),),
                datetime.now(UTC),
            )
        )
        renamed = replace(
            normalize_records([{**NATIONAL, "Naziv": "Drugi naziv"}], "national")[0],
            oib="12345678901",
        )
        await self.repo.import_snapshot(
            SourceSnapshot(self.source, (renamed,), datetime.now(UTC)),
            allow_removals=True,
        )
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM vrtici"), 1
        )
        self.assertEqual(
            await self.connection.fetchval(
                "SELECT metoda_povezivanja  AS match_method FROM izvorni_zapisi ORDER BY dohvaceno_u DESC LIMIT 1"
            ),
            "oib",
        )

    async def test_new_snapshot_removes_missing_records(self):
        other = {**NATIONAL, "Naziv": "Dječji vrtić Drugi", "Adresa": "Druga 2"}
        await self.repo.import_snapshot(self.snapshot([NATIONAL, other]))
        await self.repo.import_snapshot(self.snapshot(), allow_removals=True)
        result = await AsyncpgLocationRepository(self.connection).list_locations(
            LocationQuery(city="varazdin")
        )
        self.assertEqual([r["name"] for r in result], [NATIONAL["Naziv"]])
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM izvorni_zapisi"), 1
        )

    async def test_missing_keys_require_review_even_when_record_count_is_unchanged(
        self,
    ):
        other = {**NATIONAL, "Naziv": "DV Drugi", "Adresa": "Druga 2"}
        await self.repo.import_snapshot(self.snapshot([NATIONAL, other]))
        tables = ("izvori_podataka", "izvorni_zapisi", "vrtici", "sjedista_vrtica")
        before = {
            table: await self.connection.fetch(f"SELECT * FROM {table} ORDER BY 1")
            for table in tables
        }
        changed = {**NATIONAL, "Telefon": "new contact"}
        replacement = {**NATIONAL, "Naziv": "DV Novi", "Adresa": "Nova 3"}
        for records in ([changed], [changed, replacement]):
            with (
                self.subTest(records=len(records)),
                self.assertRaisesRegex(
                    SourceImportError,
                    "national: 1 previous source keys.*--allow-removals",
                ),
            ):
                await self.repo.import_snapshot(self.snapshot(records))
            for table in tables:
                self.assertEqual(
                    await self.connection.fetch(f"SELECT * FROM {table} ORDER BY 1"),
                    before[table],
                )

    async def test_current_state_rejects_invalid_sets_atomically_and_keeps_manual_decisions(
        self,
    ):
        from dataclasses import replace

        await self.repo.import_snapshot(self.snapshot())
        before = await self.connection.fetch(
            "SELECT id,id_izvora AS source_id,kljuc_izvornog_zapisa AS source_key,izvorni_podaci AS raw_data,dohvaceno_u AS fetched_at,datum_opazanja AS observed_on,id_vrtica AS kindergarten_id,id_objekta AS location_id,status_povezivanja AS match_status,napomena_povezivanja AS match_note,metoda_povezivanja AS match_method FROM izvorni_zapisi"
        )
        original = self.snapshot()
        for allow_removals in (False, True):
            for rows in ((), (original.rows[0], original.rows[0])):
                with self.assertRaises(SourceImportError):
                    await self.repo.import_snapshot(
                        replace(original, rows=rows), allow_removals=allow_removals
                    )
                self.assertEqual(
                    await self.connection.fetch(
                        "SELECT id,id_izvora AS source_id,kljuc_izvornog_zapisa AS source_key,izvorni_podaci AS raw_data,dohvaceno_u AS fetched_at,datum_opazanja AS observed_on,id_vrtica AS kindergarten_id,id_objekta AS location_id,status_povezivanja AS match_status,napomena_povezivanja AS match_note,metoda_povezivanja AS match_method FROM izvorni_zapisi"
                    ),
                    before,
                )
        await self.connection.execute(
            "UPDATE izvorni_zapisi SET metoda_povezivanja='manual',napomena_povezivanja='Reviewed owner'"
        )
        identity = before[0]["id"]
        await self.repo.import_snapshot(self.snapshot())
        record = await self.connection.fetchrow(
            "SELECT id,id_izvora AS source_id,kljuc_izvornog_zapisa AS source_key,izvorni_podaci AS raw_data,dohvaceno_u AS fetched_at,datum_opazanja AS observed_on,id_vrtica AS kindergarten_id,id_objekta AS location_id,status_povezivanja AS match_status,napomena_povezivanja AS match_note,metoda_povezivanja AS match_method FROM izvorni_zapisi"
        )
        self.assertEqual(
            (record["id"], record["match_method"], record["match_note"]),
            (identity, "manual", "Reviewed owner"),
        )

    async def test_current_state_clears_own_missing_contact_and_preserves_other_sources(
        self,
    ):
        from dataclasses import replace

        original = self.snapshot()
        original = replace(original, rows=(replace(original.rows[0], phone="old"),))
        await self.repo.import_snapshot(original)
        await self.repo.import_snapshot(
            replace(original, rows=(replace(original.rows[0], phone=None),))
        )
        self.assertIsNone(
            await self.connection.fetchval("SELECT telefon  AS phone FROM vrtici")
        )
        owner = await self.connection.fetchval("SELECT id FROM vrtici")
        await self.connection.execute(
            "UPDATE vrtici SET telefon='reviewed',podrijetlo=podrijetlo || $2 WHERE id=$1",
            owner,
            {"phone": {"dataset_key": "another-reviewed-source"}},
        )
        await self.repo.import_snapshot(original)
        self.assertEqual(
            await self.connection.fetchval("SELECT telefon  AS phone FROM vrtici"),
            "reviewed",
        )
        await self.connection.execute("UPDATE vrtici SET vrsta_pruzatelja='private'")
        before = await self.connection.fetch(
            "SELECT id,id_izvora AS source_id,kljuc_izvornog_zapisa AS source_key,izvorni_podaci AS raw_data,dohvaceno_u AS fetched_at,datum_opazanja AS observed_on,id_vrtica AS kindergarten_id,id_objekta AS location_id,status_povezivanja AS match_status,napomena_povezivanja AS match_note,metoda_povezivanja AS match_method FROM izvorni_zapisi"
        )
        with self.assertRaisesRegex(SourceImportError, "provider_kind"):
            await self.repo.import_snapshot(
                replace(
                    original, rows=(replace(original.rows[0], provider_kind="unknown"),)
                )
            )
        self.assertEqual(
            await self.connection.fetch(
                "SELECT id,id_izvora AS source_id,kljuc_izvornog_zapisa AS source_key,izvorni_podaci AS raw_data,dohvaceno_u AS fetched_at,datum_opazanja AS observed_on,id_vrtica AS kindergarten_id,id_objekta AS location_id,status_povezivanja AS match_status,napomena_povezivanja AS match_note,metoda_povezivanja AS match_method FROM izvorni_zapisi"
            ),
            before,
        )
        await self.connection.execute(
            "UPDATE vrtici SET podrijetlo=jsonb_set(podrijetlo,'{provider_kind}',(podrijetlo->'provider_kind')-'dataset_key')"
        )
        with self.assertRaisesRegex(SourceImportError, "provider_kind"):
            await self.repo.import_snapshot(
                replace(
                    original, rows=(replace(original.rows[0], provider_kind="unknown"),)
                )
            )
        self.assertEqual(
            await self.connection.fetch(
                "SELECT id,id_izvora AS source_id,kljuc_izvornog_zapisa AS source_key,izvorni_podaci AS raw_data,dohvaceno_u AS fetched_at,datum_opazanja AS observed_on,id_vrtica AS kindergarten_id,id_objekta AS location_id,status_povezivanja AS match_status,napomena_povezivanja AS match_note,metoda_povezivanja AS match_method FROM izvorni_zapisi"
            ),
            before,
        )

    async def test_removed_state_deletes_derived_rows_and_dangling_provenance(self):
        second = {**NATIONAL, "Naziv": "DV Drugi", "Adresa": "Druga 2"}
        await self.repo.import_snapshot(self.snapshot([NATIONAL, second]))
        record = await self.connection.fetchrow(
            "SELECT id,id_izvora AS source_id,kljuc_izvornog_zapisa AS source_key,izvorni_podaci AS raw_data,dohvaceno_u AS fetched_at,datum_opazanja AS observed_on,id_vrtica AS kindergarten_id,id_objekta AS location_id,status_povezivanja AS match_status,napomena_povezivanja AS match_note,metoda_povezivanja AS match_method FROM izvorni_zapisi WHERE izvorni_podaci->>'Naziv'='DV Drugi'"
        )
        await self.connection.execute(
            "INSERT INTO odlomci_znanja(id_vrtica,id_izvornog_zapisa,redni_broj,sadrzaj,poveznica_izvora) VALUES ($1,$2,0,'Test','https://example.invalid')",
            record["kindergarten_id"],
            record["id"],
        )
        await self.connection.execute(
            "INSERT INTO upisni_krugovi(id_vrtica,id_izvornog_zapisa,pedagoska_godina,poveznica_za_prijavu,kanal_prijave) VALUES ($1,$2,'2026/27','https://example.invalid','kindergarten')",
            record["kindergarten_id"],
            record["id"],
        )
        with self.assertRaises(SourceImportError):
            await self.repo.import_snapshot(self.snapshot())
        for table in ("odlomci_znanja", "upisni_krugovi"):
            self.assertEqual(
                await self.connection.fetchval(f"SELECT count(*) FROM {table}"), 1
            )
        await self.repo.import_snapshot(self.snapshot(), allow_removals=True)
        for table in ("odlomci_znanja", "upisni_krugovi"):
            self.assertEqual(
                await self.connection.fetchval(f"SELECT count(*) FROM {table}"), 0
            )
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM izvorni_zapisi"), 1
        )
        self.assertEqual(
            await self.connection.fetchval(
                "SELECT podrijetlo  AS provenance FROM vrtici WHERE id=$1",
                record["kindergarten_id"],
            ),
            {},
        )

    async def test_seat_migration_rejects_county_disagreements(self):
        import asyncpg

        await self.repo.import_snapshot(self.snapshot())
        await self.connection.execute(
            "ALTER TABLE vrtici ADD COLUMN seat_county text, ADD COLUMN seat_municipality_id uuid"
        )
        await self.connection.execute("ALTER TABLE objekti ADD COLUMN zupanija text")
        await self.connection.execute(
            "UPDATE vrtici SET seat_county='Wrong county',seat_municipality_id=(SELECT id FROM jedinice_lokalne_samouprave WHERE kljuc='varazdin')"
        )
        check = (
            (
                Path(__file__).resolve().parents[1]
                / "src/KIDSic/db/alembic/versions/0013_kindergarten_seat.sql"
            )
            .read_text()
            .split("\n-- statement\n")[0]
        )
        with self.assertRaisesRegex(
            asyncpg.RaiseError, "Review county differences.*Wrong county"
        ):
            async with self.connection.transaction():
                await self.connection.execute(current_table_names(check))
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM sjedista_vrtica"), 1
        )

    async def test_removing_geography_clears_the_seat_foreign_key_and_coordinates(self):
        from KIDSic.dao.concrete.source_state import SourceStateWriter

        await self.repo.import_snapshot(
            self.snapshot([NATIONAL, {**NATIONAL, "Naziv": "DV Drugi"}])
        )
        owners = [
            r["id"]
            for r in await self.connection.fetch("SELECT id FROM vrtici ORDER BY id")
        ]
        source = await self.connection.fetchval(
            "INSERT INTO izvori_podataka(kljuc_skupa_podataka,naslov,izdavac,poveznica,uvoz_dopusten) VALUES ('geography','Geo','Test','https://example.invalid/geo',true) RETURNING id"
        )
        state = SourceStateWriter(self.connection, source, datetime.now(UTC))
        record = await state.record("one", {}, owner=owners[0])
        await state.record("two", {}, owner=owners[1])
        await state.finish()
        await self.connection.execute(
            "UPDATE sjedista_vrtica SET id_zapisa_geografskog_izvora=$2,geografska_duzina=16.3,geografska_sirina=46.3,obiljezja=jsonb_build_object('address',adresa) WHERE id_vrtica=$1",
            owners[0],
            record,
        )
        next_state = SourceStateWriter(self.connection, source, datetime.now(UTC))
        await next_state.record("two", {}, owner=owners[1])
        await next_state.finish()
        seat = await self.connection.fetchrow(
            "SELECT id_zapisa_geografskog_izvora AS geography_source_record_id,geografska_duzina AS longitude,geografska_sirina  AS latitude FROM sjedista_vrtica WHERE id_vrtica=$1",
            owners[0],
        )
        self.assertEqual(tuple(seat), (None, None, None))
        self.assertFalse(
            await self.connection.fetchval(
                "SELECT EXISTS(SELECT 1 FROM izvorni_zapisi WHERE id=$1)", record
            )
        )

    async def test_ambiguous_match_is_retained_for_review(self):
        for name in ("DV Primjer", 'Dječji vrtić "Primjer"'):
            owner = await self.connection.fetchval(
                "INSERT INTO vrtici(naziv) VALUES ($1) RETURNING id", name
            )
            await self.connection.execute(
                "INSERT INTO objekti(id_vrtica,naziv,naselje,kljuc_naselja,adresa) VALUES ($1,$2,'Varaždin','varazdin','Primjer 1')",
                owner,
                name,
            )
        second = {**NATIONAL, "Naziv": "DV Drugi", "Adresa": "Druga 2"}
        result = await self.repo.import_snapshot(self.snapshot([NATIONAL, second]))
        self.assertEqual(result["needs_review"], 1)
        self.assertEqual(
            await self.connection.fetchval(
                "SELECT count(*) FROM izvorni_zapisi WHERE status_povezivanja='candidate'"
            ),
            1,
        )

    async def test_later_failure_rolls_back_all_sources_in_service_transaction(self):
        @asynccontextmanager
        async def work():
            async with self.connection.transaction():
                yield SimpleNamespace(sources=self.repo)

        second_client = source_client("municipal")
        second_client.download_records.return_value = [MUNICIPAL]
        second_definition = SourceDefinition(
            "zagreb-municipal",
            "https://data.zagreb.hr",
            "gradski_vrtici_grada_zagreba",
            "municipal",
        )
        second_source = PlannedSource(
            second_definition,
            second_client.get_package.return_value,
            second_client.get_package.return_value.resources[0],
        )
        await self.repo.register(second_source)
        await self.connection.execute(
            "UPDATE izvori_podataka SET uvoz_dopusten=false WHERE kljuc_skupa_podataka='zagreb-municipal'"
        )
        service = source_service(
            {"national": self.client, "zagreb-municipal": second_client},
            [self.definition, second_definition],
            work,
        )
        with self.assertRaises(SourceImportError):
            await service.import_data()
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM vrtici"), 0
        )
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM izvorni_zapisi"), 0
        )
        self.assertEqual(
            await self.connection.fetchval(
                "SELECT count(*) FROM izvori_podataka WHERE kljuc_skupa_podataka='national'"
            ),
            0,
        )

    async def test_partial_later_resource_rolls_back_earlier_source_changes(self):
        @asynccontextmanager
        async def work():
            async with self.connection.transaction():
                yield SimpleNamespace(sources=self.repo)

        other = source_client("municipal")
        branch = {
            **MUNICIPAL,
            "Id": 2,
            "Naziv": "DV Primjer-PO Druga",
            "Adresa": "Druga 2",
        }
        other.download_records.return_value = [MUNICIPAL, branch]
        municipal = self.municipal_source()
        service = source_service(
            {"national": self.client, municipal.definition.key: other},
            [self.definition, municipal.definition],
            work,
        )
        await service.import_data()
        tables = (
            "izvori_podataka",
            "izvorni_zapisi",
            "vrtici",
            "sjedista_vrtica",
            "objekti",
        )
        before = {
            table: await self.connection.fetch(f"SELECT * FROM {table} ORDER BY 1")
            for table in tables
        }
        self.client.download_records.return_value = [
            {**NATIONAL, "Telefon": "new contact"}
        ]
        other.download_records.return_value = [MUNICIPAL]
        with self.assertRaisesRegex(
            SourceImportError, "previous source keys are missing"
        ):
            await service.import_data()
        for table in tables:
            self.assertEqual(
                await self.connection.fetch(f"SELECT * FROM {table} ORDER BY 1"),
                before[table],
            )
        await service.import_data(allow_removals=True)
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM izvorni_zapisi"), 2
        )
        removed = await self.connection.fetchrow(
            "SELECT vrsta AS kind,podrijetlo  AS provenance FROM objekti WHERE adresa IS NULL"
        )
        self.assertEqual(removed["kind"], "unknown")
        self.assertEqual(removed["provenance"], {})

    async def test_writer_translates_driver_errors_and_releases_the_connection(self):
        import asyncpg

        before = self.pool.get_size() - self.pool.get_idle_size()
        with self.assertRaises(PersistenceError) as error:
            async with AsyncpgSourceUnitOfWork(self.pool):
                raise asyncpg.PostgresError("synthetic database failure")
        self.assertIsInstance(error.exception.__cause__, asyncpg.PostgresError)
        self.assertEqual(self.pool.get_size() - self.pool.get_idle_size(), before)

    async def test_writer_unit_of_work_rolls_back_and_releases_connection(self):
        before = self.pool.get_size() - self.pool.get_idle_size()
        with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
            async with AsyncpgSourceUnitOfWork(self.pool) as work:
                await work.sources.register(self.source)
                raise RuntimeError("synthetic failure")
        self.assertEqual(self.pool.get_size() - self.pool.get_idle_size(), before)
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM izvori_podataka"), 0
        )

    @unittest.skipUnless(
        os.getenv("KIDSIC_CKAN_SIMULATION_URL"), "Start the CKAN Postman simulation"
    )
    async def test_full_http_to_database_path_preserves_snapshot_on_download_failure(
        self,
    ):
        @asynccontextmanager
        async def work():
            async with self.connection.transaction():
                yield SimpleNamespace(sources=self.repo)

        url = os.environ["KIDSIC_CKAN_SIMULATION_URL"]
        settings = Settings(
            database_url=os.environ["KIDSIC_TEST_DATABASE_URL"],
            ckan_base_url=url,
            ckan_zagreb_base_url=url,
        )
        async with httpx.AsyncClient() as http:
            result = (
                await SourceServiceFactory(settings)
                .create(
                    http,
                    work,
                    source_keys=["national", "zagreb-municipal", "zagreb-other"],
                )
                .import_data()
            )
            self.assertEqual(result["records"], 4)
            self.assertEqual(
                await self.connection.fetchval("SELECT count(*) FROM vrtici"), 2
            )
            self.assertEqual(
                await self.connection.fetchval("SELECT count(*) FROM objekti"), 3
            )
            before = await self.connection.fetch(
                "SELECT kljuc_skupa_podataka AS dataset_key,dohvaceno_u  AS fetched_at FROM izvori_podataka ORDER BY kljuc_skupa_podataka"
            )
            broken = Settings(
                database_url=settings.database_url,
                ckan_base_url=url,
                ckan_zagreb_base_url=url,
                ckan_zagreb_other_dataset_id="broken-download",
            )
            from KIDSic.exceptions import CkanHttpError

            with self.assertRaises(CkanHttpError):
                await (
                    SourceServiceFactory(broken)
                    .create(
                        http,
                        work,
                        source_keys=["national", "zagreb-municipal", "zagreb-other"],
                    )
                    .import_data()
                )
            self.assertEqual(
                await self.connection.fetch(
                    "SELECT kljuc_skupa_podataka AS dataset_key,dohvaceno_u  AS fetched_at FROM izvori_podataka ORDER BY kljuc_skupa_podataka"
                ),
                before,
            )
