"""Rollback-only fixtures protect identity matching and historical evidence scopes."""

from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from support.database import DatabaseTestCase
from support.historical import (
    DEFINITIONS,
    PROGRAMS,
    historical_parser,
    historical_service,
    municipal_table,
    package,
)
from support.sources import MUNICIPAL, source_client

from KIDSic.dao.concrete.asyncpg_historical import AsyncpgHistoricalRepository
from KIDSic.dao.concrete.asyncpg_location import AsyncpgLocationRepository
from KIDSic.dao.concrete.asyncpg_source import AsyncpgSourceRepository
from KIDSic.dto.historical import HistoricalSnapshot
from KIDSic.dto.location import LocationQuery
from KIDSic.dto.source import PlannedSource, SourceSnapshot
from KIDSic.exceptions import SourceImportError
from KIDSic.services.concrete.kindergarten_normalizer import normalize_records


class HistoricalDatabaseTests(DatabaseTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.directory = AsyncpgSourceRepository(self.connection)
        self.history = AsyncpgHistoricalRepository(self.connection)
        from KIDSic.dto.source import SourceDefinition

        client = source_client("municipal")
        definition = SourceDefinition(
            "directory", "https://example.invalid", "directory", "municipal"
        )
        source = PlannedSource(
            definition,
            client.get_package.return_value,
            client.get_package.return_value.resources[0],
        )
        rows = normalize_records(
            [
                MUNICIPAL,
                {
                    **MUNICIPAL,
                    "Id": 2,
                    "Naziv": "DV Primjer-PO Druga",
                    "Adresa": "Druga 2",
                    "TipVrtica": "Područni",
                },
            ],
            "municipal",
        )
        await self.directory.import_snapshot(
            SourceSnapshot(source, rows, datetime.now(UTC))
        )

    async def snapshot(self, index=0, table=None):
        definition = DEFINITIONS[index]
        metadata = package(definition)
        source = PlannedSource(definition.source, metadata, metadata.resources[0])
        await self.directory.register(source)
        rows = historical_parser().parse(
            table or (PROGRAMS if index == 0 else municipal_table()), definition
        )
        return HistoricalSnapshot(
            source,
            rows,
            datetime.now(UTC),
            definition.reference_date,
            definition.date_kind,
        )

    async def test_facility_programs_and_institution_counts_keep_separate_scopes(self):
        before = await self.connection.fetch(
            "SELECT id,id_vrtica AS kindergarten_id,adresa  AS address FROM objekti ORDER BY id"
        )
        await self.history.import_snapshot(await self.snapshot())
        await self.history.import_snapshot(await self.snapshot(1))
        rows = await AsyncpgLocationRepository(self.connection).list_locations(
            LocationQuery()
        )
        self.assertEqual(len(rows), 2)
        main = next(r for r in rows if r["address"] == "Primjer 1")
        branch = next(r for r in rows if r["address"] == "Druga 2")
        self.assertEqual(len(main["historical_data"]), 2)
        self.assertEqual(
            len(branch["historical_data"]), 1
        )  # slash is not evidence of a program
        self.assertEqual(
            main["historical_data"][1]["programs"], ["Montessori", "engleski jezik"]
        )
        self.assertEqual(main["historical_data"][0]["scope"], "institution")
        self.assertEqual(main["historical_data"][0]["reference_date"], "2025-01-01")
        self.assertEqual(
            str(
                await self.connection.fetchval(
                    "SELECT datum_opazanja  AS observed_on FROM izvori_podataka WHERE kljuc_skupa_podataka='zagreb-vacancies-2025'"
                )
            ),
            "2025-01-01",
        )
        self.assertIsNone(
            await self.connection.fetchval(
                "SELECT datum_opazanja  AS observed_on FROM izvori_podataka WHERE kljuc_skupa_podataka='zagreb-programs-2019'"
            )
        )
        self.assertEqual(
            sum(v["free_places"] for v in main["historical_data"][0]["vacancies"]), 5
        )
        self.assertEqual(
            await self.connection.fetch(
                "SELECT id,id_vrtica AS kindergarten_id,adresa  AS address FROM objekti ORDER BY id"
            ),
            before,
        )

    async def test_reimport_preserves_identity_and_revocation_hides_history(self):
        snapshot = await self.snapshot()
        await self.history.import_snapshot(snapshot)
        identities = await self.connection.fetch(
            "SELECT kljuc_izvornog_zapisa AS source_key,id FROM povijesni_zapisi ORDER BY kljuc_izvornog_zapisa"
        )
        await self.history.import_snapshot(snapshot)
        self.assertEqual(
            await self.connection.fetch(
                "SELECT kljuc_izvornog_zapisa AS source_key,id FROM povijesni_zapisi ORDER BY kljuc_izvornog_zapisa"
            ),
            identities,
        )
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM povijesni_zapisi"), 2
        )
        repo = AsyncpgLocationRepository(self.connection)
        self.assertEqual(
            sum(
                len(r["historical_data"])
                for r in await repo.list_locations(LocationQuery())
            ),
            1,
        )
        await self.connection.execute(
            "UPDATE izvori_podataka SET uvoz_dopusten=false WHERE kljuc_skupa_podataka=$1",
            snapshot.source.definition.key,
        )
        self.assertTrue(
            all(
                not r["historical_data"]
                for r in await repo.list_locations(LocationQuery())
            )
        )
        with self.assertRaises(SourceImportError):
            await self.history.import_snapshot(snapshot)

    async def test_reimport_updates_contents_and_removes_missing_historical_keys(self):
        snapshot = await self.snapshot()
        await self.history.import_snapshot(snapshot)
        kept = snapshot.rows[0]
        identity = await self.connection.fetchval(
            "SELECT id FROM povijesni_zapisi WHERE kljuc_izvornog_zapisa=$1",
            kept.source_key,
        )
        changed = replace(
            kept, programs=("Updated program",), raw_data={"reviewed": "new content"}
        )
        await self.history.import_snapshot(replace(snapshot, rows=(changed,)))
        [row] = await self.connection.fetch(
            "SELECT id,id_izvora AS source_id,kljuc_izvornog_zapisa AS source_key,izvorni_podaci AS raw_data,id_vrtica AS kindergarten_id,id_objekta AS location_id,obuhvat AS scope,status_povezivanja AS match_status,referentni_datum AS reference_date,vrsta_datuma AS date_kind,dohvaceno_u AS fetched_at,programi AS programs,slobodna_mjesta AS vacancies FROM povijesni_zapisi"
        )
        self.assertEqual(row["id"], identity)
        self.assertEqual(row["programs"], ["Updated program"])
        self.assertEqual(row["raw_data"], {"reviewed": "new content"})
        before = dict(row)
        for rows in ((), (changed, changed), (replace(changed, name="No match"),)):
            with self.subTest(rows=len(rows)), self.assertRaises(SourceImportError):
                await self.history.import_snapshot(replace(snapshot, rows=rows))
            self.assertEqual(
                dict(
                    await self.connection.fetchrow(
                        "SELECT id,id_izvora AS source_id,kljuc_izvornog_zapisa AS source_key,izvorni_podaci AS raw_data,id_vrtica AS kindergarten_id,id_objekta AS location_id,obuhvat AS scope,status_povezivanja AS match_status,referentni_datum AS reference_date,vrsta_datuma AS date_kind,dohvaceno_u AS fetched_at,programi AS programs,slobodna_mjesta AS vacancies FROM povijesni_zapisi"
                    )
                ),
                before,
            )

    async def test_unmatched_rows_require_review_and_failed_import_preserves_current_state(
        self,
    ):
        table = PROGRAMS + [
            ["DV Nepostojeći", "Nepostojeća 99", "Gradski vrtić", "Montessori"]
        ]
        result = await self.history.import_snapshot(await self.snapshot(table=table))
        self.assertEqual((result["accepted"], result["needs_review"]), (2, 1))
        self.assertEqual(
            await self.connection.fetchval(
                "SELECT count(*) FROM povijesni_zapisi WHERE status_povezivanja='candidate' AND id_vrtica IS NULL"
            ),
            1,
        )
        before = await self.connection.fetch(
            "SELECT id,dohvaceno_u  AS fetched_at FROM izvori_podataka ORDER BY id"
        )
        snapshot = await self.snapshot()
        bad = replace(snapshot, rows=(replace(snapshot.rows[0], name="No match"),))
        with self.assertRaises(SourceImportError):
            async with self.connection.transaction():
                await self.history.import_snapshot(bad)
        self.assertEqual(
            await self.connection.fetch(
                "SELECT id,dohvaceno_u  AS fetched_at FROM izvori_podataka ORDER BY id"
            ),
            before,
        )

    async def test_provider_conflicts_and_ambiguous_addresses_never_link_automatically(
        self,
    ):
        snapshot = await self.snapshot()
        bad = replace(snapshot.rows[0], source_key="mismatch", provider_kind="private")
        result = await self.history.import_snapshot(
            replace(snapshot, rows=(snapshot.rows[1], bad))
        )
        self.assertEqual((result["accepted"], result["needs_review"]), (1, 1))
        await self.connection.execute("""INSERT INTO objekti(id_vrtica,naziv,adresa,naselje,kljuc_naselja,id_jedinice_lokalne_samouprave)
            SELECT id_vrtica AS kindergarten_id,naziv AS name,adresa AS address,naselje AS settlement,kljuc_naselja AS settlement_key,id_jedinice_lokalne_samouprave  AS municipality_id FROM objekti WHERE adresa='Primjer 1' """)
        # An unattested duplicate cannot anchor a match; active duplicates are ambiguous.
        await self.connection.execute("""INSERT INTO izvorni_zapisi(id_izvora,izvorni_podaci,id_vrtica,id_objekta,status_povezivanja,metoda_povezivanja)
            SELECT s.id,'{}',l.id_vrtica AS kindergarten_id,l.id,'accepted','manual' FROM objekti l CROSS JOIN izvori_podataka s
            WHERE s.kljuc_skupa_podataka='directory' AND NOT EXISTS(SELECT 1 FROM izvorni_zapisi r WHERE r.id_objekta=l.id)""")
        result = await self.history.import_snapshot(snapshot)
        self.assertEqual((result["accepted"], result["needs_review"]), (1, 1))

    async def test_same_name_and_address_outside_zagreb_cannot_anchor_history(self):
        municipality = await self.connection.fetchval(
            "INSERT INTO jedinice_lokalne_samouprave(kljuc,naziv) VALUES ('rijeka','Rijeka') RETURNING id"
        )
        owner = await self.connection.fetchval(
            "INSERT INTO vrtici(naziv,vrsta_pruzatelja) VALUES ('DV Primjer','municipal') RETURNING id"
        )
        location = await self.connection.fetchval(
            """INSERT INTO objekti(id_vrtica,naziv,adresa,naselje,kljuc_naselja,id_jedinice_lokalne_samouprave)
            VALUES($1,'DV Primjer','Primjer 1','Rijeka','rijeka',$2) RETURNING id""",
            owner,
            municipality,
        )
        await self.connection.execute(
            """INSERT INTO izvorni_zapisi(id_izvora,izvorni_podaci,id_vrtica,id_objekta,status_povezivanja,metoda_povezivanja)
            SELECT id,'{}',$1,$2,'accepted','manual' FROM izvori_podataka WHERE kljuc_skupa_podataka='directory' """,
            owner,
            location,
        )
        result = await self.history.import_snapshot(await self.snapshot())
        self.assertEqual(result["accepted"], 2)
        rows = await AsyncpgLocationRepository(self.connection).list_locations(
            LocationQuery(city="Rijeka")
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["historical_data"], [])

    async def test_failure_in_later_source_rolls_back_registration_and_previous_source(
        self,
    ):
        snapshot = await self.snapshot(1)
        await self.connection.execute(
            "UPDATE izvori_podataka SET uvoz_dopusten=false WHERE kljuc_skupa_podataka=$1",
            snapshot.source.definition.key,
        )
        before = await self.connection.fetch(
            "SELECT id,dohvaceno_u  AS fetched_at FROM izvori_podataka ORDER BY id"
        )
        definitions = DEFINITIONS[:2]
        clients = {
            d.source.key: SimpleNamespace(
                get_package=AsyncMock(return_value=package(d)),
                download_table=AsyncMock(return_value=table),
            )
            for d, table in zip(definitions, (PROGRAMS, municipal_table()))
        }

        @asynccontextmanager
        async def work():
            async with self.connection.transaction():
                yield SimpleNamespace(sources=self.directory, historical=self.history)

        with self.assertRaises(SourceImportError):
            await historical_service(clients, definitions, work).import_data()
        self.assertEqual(
            await self.connection.fetch(
                "SELECT id,dohvaceno_u  AS fetched_at FROM izvori_podataka ORDER BY id"
            ),
            before,
        )
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM povijesni_zapisi"), 0
        )

    async def test_rag_reads_history_and_document_chunks_only_for_selected_active_object(
        self,
    ):
        from KIDSic.dao.concrete.asyncpg_kindergarten import (
            AsyncpgKindergartenRepository,
        )
        from KIDSic.dto.rag import RagQuery
        from KIDSic.factories.rag import RagServiceFactory

        await self.history.import_snapshot(await self.snapshot())

        @asynccontextmanager
        async def work():
            yield SimpleNamespace(
                locations=AsyncpgLocationRepository(self.connection),
                search=AsyncpgKindergartenRepository(self.connection),
            )

        service = RagServiceFactory().create(work)
        locations = await self.connection.fetch(
            "SELECT id,id_vrtica AS kindergarten_id,adresa  AS address FROM objekti ORDER BY adresa"
        )
        main = next(l for l in locations if l["address"] == "Primjer 1")
        for location in locations:
            record = await self.connection.fetchval(
                "SELECT id FROM izvorni_zapisi WHERE id_objekta=$1", location["id"]
            )
            await self.connection.execute(
                """INSERT INTO odlomci_znanja(id_vrtica,id_objekta,id_izvornog_zapisa,redni_broj,sadrzaj,poveznica_izvora)
                VALUES($1,$2,$3,0,$4,'https://example.invalid/upis')""",
                location["kindergarten_id"],
                location["id"],
                record,
                "Dokumenti za upis: " + location["address"],
            )
        query = RagQuery(
            city="Zagreb",
            name="Primjer",
            topics=["programs"],
            feature_id=str(main["id"]),
        )
        result = await service.retrieve(query)
        self.assertEqual(len(result.evidence), 1)
        self.assertEqual(result.evidence[0].temporal_status, "historical")
        documents = await service.retrieve(
            query.model_copy(update={"topics": ["document"]})
        )
        self.assertEqual(len(documents.evidence), 1)
        self.assertIn("Primjer 1", documents.evidence[0].content)
        self.assertNotIn("Druga 2", documents.evidence[0].content)
        await self.connection.execute(
            "UPDATE izvori_podataka SET uvoz_dopusten=false WHERE kljuc_skupa_podataka='zagreb-programs-2019'"
        )
        self.assertEqual((await service.retrieve(query)).status, "no_evidence")
        await self.connection.execute(
            "UPDATE izvori_podataka SET uvoz_dopusten=false WHERE kljuc_skupa_podataka='directory'"
        )
        self.assertEqual((await service.retrieve(query)).status, "not_found")
