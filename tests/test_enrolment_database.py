"""Rollback-only fixtures protect enrolment document scope, dates and revocation."""

import unittest
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

from support.database import DatabaseTestCase
from support.enrolment import CALL, DOCUMENT
from support.sources import MUNICIPAL, source_client

from KIDSic.dao.concrete.asyncpg_enrolment import AsyncpgEnrolmentDocumentRepository
from KIDSic.dao.concrete.asyncpg_kindergarten import AsyncpgKindergartenRepository
from KIDSic.dao.concrete.asyncpg_location import AsyncpgLocationRepository
from KIDSic.dao.concrete.asyncpg_source import AsyncpgSourceRepository
from KIDSic.dto.enrolment import EnrolmentDocument
from KIDSic.dto.location import LocationQuery
from KIDSic.dto.rag import RagQuery
from KIDSic.dto.source import PlannedSource, SourceDefinition, SourceSnapshot
from KIDSic.exceptions import SourceImportError
from KIDSic.factories.rag import RagServiceFactory
from KIDSic.services.concrete.kindergarten_normalizer import normalize_records


class EnrolmentDatabaseTests(DatabaseTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        client = source_client("municipal")
        definition = SourceDefinition(
            "directory", "https://example.invalid", "directory", "municipal"
        )
        package = client.get_package.return_value
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
        await AsyncpgSourceRepository(self.connection).import_snapshot(
            SourceSnapshot(
                PlannedSource(definition, package, package.resources[0]),
                rows,
                datetime.now(UTC),
            )
        )
        self.enrolment = AsyncpgEnrolmentDocumentRepository(self.connection)

        @asynccontextmanager
        async def work():
            yield SimpleNamespace(
                locations=AsyncpgLocationRepository(self.connection),
                search=AsyncpgKindergartenRepository(self.connection),
            )

        self.rag = RagServiceFactory().create(work)
        self.query = RagQuery(city="Zagreb", name="Primjer", topics=["document"])

    async def load(self, **changes):
        document = EnrolmentDocument.model_validate({**DOCUMENT, **changes})
        return await self.enrolment.import_document(
            document, "test-snapshot", datetime.now(UTC)
        )

    async def add_owner(self, name, provider="municipal"):
        owner = await self.connection.fetchval(
            "INSERT INTO vrtici(naziv,vrsta_pruzatelja) VALUES ($1,$2) RETURNING id",
            name,
            provider,
        )
        location = await self.connection.fetchval(
            "INSERT INTO objekti(id_vrtica,naziv,naselje,kljuc_naselja,id_jedinice_lokalne_samouprave) VALUES ($1,$2,'Zagreb','zagreb',(SELECT id FROM jedinice_lokalne_samouprave WHERE kljuc='zagreb')) RETURNING id",
            owner,
            name,
        )
        await self.connection.execute(
            "INSERT INTO izvorni_zapisi(id_izvora,kljuc_izvornog_zapisa,izvorni_podaci,id_vrtica,id_objekta,status_povezivanja,metoda_povezivanja) SELECT id,$1,'{}',$2,$3,'accepted','manual' FROM izvori_podataka WHERE kljuc_skupa_podataka='directory'",
            str(owner),
            owner,
            location,
        )
        return owner, location

    async def test_shared_rule_excludes_private_providers_and_includes_later_municipal_owners(
        self,
    ):
        await self.add_owner("Privatni primjer", "private")
        await self.load(calls=[CALL])
        source_records = await self.connection.fetchval(
            "SELECT count(*) FROM izvorni_zapisi r JOIN izvori_podataka s ON s.id=r.id_izvora WHERE s.kljuc_skupa_podataka='example-enrolment'"
        )
        self.assertEqual(source_records, 1)
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM upisni_krugovi"), 1
        )
        owner, location = await self.add_owner("Kasniji gradski vrtić")
        rows = await AsyncpgLocationRepository(self.connection).list_locations(
            LocationQuery(city="Zagreb")
        )
        private = next(r for r in rows if r["provider_kind"] == "private")
        later = next(r for r in rows if r["kindergarten_id"] == owner)
        self.assertEqual(private["enrolment"], [])
        self.assertEqual(len(later["enrolment"]), 1)
        later_context = await self.rag.retrieve(
            RagQuery(city="Zagreb", name="Kasniji", topics=["document"])
        )
        self.assertEqual(
            (later_context.status, later_context.evidence[0].scope),
            ("ok", "municipality"),
        )
        self.assertEqual(later_context.evidence[0].applies_to, [str(location)])
        self.assertEqual(
            (
                await self.rag.retrieve(
                    RagQuery(city="Zagreb", name="Privatni", topics=["document"])
                )
            ).status,
            "no_evidence",
        )

    async def test_named_document_never_reaches_another_municipal_owner(self):
        await self.add_owner("Drugi gradski vrtić")
        await self.load(institutions=["Dječji vrtić Primjer"], calls=[CALL])
        other = await self.rag.retrieve(
            RagQuery(city="Zagreb", name="Drugi", topics=["document"])
        )
        self.assertEqual(other.status, "no_evidence")
        rows = await AsyncpgLocationRepository(self.connection).list_locations(
            LocationQuery(city="Zagreb", q="Drugi")
        )
        self.assertEqual(rows[0]["enrolment"], [])

    async def test_ownerless_accepted_evidence_requires_a_scope_at_commit(self):
        import asyncpg

        with self.assertRaises(asyncpg.CheckViolationError):
            async with self.connection.transaction():
                await self.connection.execute(
                    "INSERT INTO izvorni_zapisi(id_izvora,kljuc_izvornog_zapisa,izvorni_podaci,status_povezivanja,metoda_povezivanja) SELECT id,'unscoped','{}','accepted','manual' FROM izvori_podataka WHERE kljuc_skupa_podataka='directory'"
                )
                await self.connection.execute("SET CONSTRAINTS ALL IMMEDIATE")

    async def test_municipal_and_named_excerpts_reach_every_object_with_dates_and_licence(
        self,
    ):
        result = await self.load(
            valid_until=(date.today() + timedelta(days=30)).isoformat(),
            excerpts=[
                {
                    "content": "Zahtjevi se podnose od 13. svibnja 2026. do 22. svibnja 2026."
                },
                {
                    "content": "Ovaj vrtić ne provodi upise.",
                    "institutions": ["Dječji vrtić Primjer"],
                },
            ],
        )
        self.assertEqual(
            (result["institutions"], result["records"], result["chunks"]), (1, 2, 2)
        )
        context = await self.rag.retrieve(self.query)
        self.assertEqual((context.status, context.total_matches), ("ok", 2))
        by_scope = {e.scope: e for e in context.evidence}
        self.assertEqual(set(by_scope), {"municipality", "institution"})
        for item in context.evidence:
            self.assertEqual(
                len(item.applies_to), 2
            )
            self.assertEqual(
                (item.reference_date, item.date_kind, item.temporal_status),
                (date(2026, 5, 11), "published", "current"),
            )
            self.assertEqual(item.sources[0].url, "https://example.invalid/upis.pdf")
            self.assertEqual(
                item.sources[0].license, "Ponovna uporaba uz navođenje izvora"
            )
        self.assertIsNone(
            await self.connection.fetchval(
                "SELECT datum_opazanja  AS observed_on FROM izvori_podataka WHERE kljuc_skupa_podataka='example-enrolment'"
            )
        )

    async def test_rounds_reach_every_object_of_the_institution_with_source_dates(self):
        result = await self.load(
            calls=[
                CALL,
                {
                    **CALL,
                    "round": "rolling",
                    "opens_at": None,
                    "closes_at": "2999-08-31T23:59:59+02:00",
                },
            ]
        )
        self.assertEqual(result["enrolment_rounds"], 2)
        rows = await AsyncpgLocationRepository(self.connection).list_locations(
            LocationQuery(city="Zagreb", q="Primjer")
        )
        self.assertEqual(len(rows), 2)
        for row in rows:
            rounds = {r["round"]: r for r in row["enrolment"]}
            self.assertEqual(set(rounds), {"main", "rolling"})
            self.assertEqual(
                (
                    rounds["main"]["application_url"],
                    rounds["main"]["channel"],
                    rounds["main"]["accepting"],
                ),
                ("https://upis.example.invalid/", "city_system", True),
            )
            self.assertEqual(
                (rounds["main"]["reference_date"], rounds["main"]["date_kind"]),
                ("2026-05-11", "published"),
            )
            self.assertEqual(
                rounds["main"]["source_url"], "https://example.invalid/upis.pdf"
            )
        await self.connection.execute(
            "UPDATE izvori_podataka SET uvoz_dopusten=false WHERE kljuc_skupa_podataka='example-enrolment'"
        )
        rows = await AsyncpgLocationRepository(self.connection).list_locations(
            LocationQuery(city="Zagreb", q="Primjer")
        )
        self.assertEqual([r["enrolment"] for r in rows], [[], []])

    async def test_reimport_keeps_only_the_active_rounds_and_records_refusals(self):
        await self.load(calls=[CALL])
        await self.load(calls=[{**CALL, "not_accepting": ["Dječji vrtić Primjer"]}])
        [row, _] = await AsyncpgLocationRepository(self.connection).list_locations(
            LocationQuery(city="Zagreb", q="Primjer")
        )
        self.assertEqual([r["accepting"] for r in row["enrolment"]], [False])
        with self.assertRaisesRegex(SourceImportError, "0 active institutions"):
            await self.load(
                calls=[{**CALL, "not_accepting": ["Dječji vrtić Nepostojeći"]}]
            )

    async def test_expired_period_is_historical_and_observed_date_is_kept(self):
        await self.load(
            reference_date="2020-05-11", date_kind="observed", valid_until="2021-08-31"
        )
        [item] = (await self.rag.retrieve(self.query)).evidence
        self.assertEqual(
            (item.reference_date, item.date_kind, item.temporal_status),
            (date(2020, 5, 11), "observed", "historical"),
        )
        self.assertEqual(
            await self.connection.fetchval(
                "SELECT datum_opazanja  AS observed_on FROM izvori_podataka WHERE kljuc_skupa_podataka='example-enrolment'"
            ),
            date(2020, 5, 11),
        )

    async def test_reimport_updates_document_in_place_and_revocation_hides_evidence(
        self,
    ):
        await self.load()
        record = await self.connection.fetchval(
            "SELECT r.id FROM izvorni_zapisi r JOIN izvori_podataka s ON s.id=r.id_izvora WHERE s.kljuc_skupa_podataka='example-enrolment'"
        )
        await self.load(excerpts=[{"content": "Nova verzija obavijesti."}])
        self.assertEqual(
            await self.connection.fetchval(
                "SELECT r.id FROM izvorni_zapisi r JOIN izvori_podataka s ON s.id=r.id_izvora WHERE s.kljuc_skupa_podataka='example-enrolment'"
            ),
            record,
        )
        [item] = (await self.rag.retrieve(self.query)).evidence
        self.assertEqual(item.content, "Nova verzija obavijesti.")
        await self.connection.execute(
            "UPDATE izvori_podataka SET uvoz_dopusten=false WHERE kljuc_skupa_podataka='example-enrolment'"
        )
        self.assertEqual((await self.rag.retrieve(self.query)).status, "no_evidence")
        with self.assertRaisesRegex(SourceImportError, "disabled"):
            await self.load()

    async def test_typed_dates_update_in_place_and_json_cannot_override_them(self):
        await self.load(
            calls=[CALL],
            reference_date="2020-05-11",
            date_kind="observed",
            valid_until="2021-08-31",
        )
        record = await self.connection.fetchval(
            "SELECT id_izvornog_zapisa  AS source_record_id FROM zapisi_dokumenata"
        )
        source = await self.connection.fetchrow(
            "SELECT vrsta AS kind,metapodaci  AS metadata FROM izvori_podataka WHERE kljuc_skupa_podataka='example-enrolment'"
        )
        self.assertEqual(source["kind"], "enrolment_document")
        self.assertNotIn("kind", source["metadata"])
        self.assertEqual(source["metadata"]["snapshot_key"], "test-snapshot")
        self.assertEqual(
            await self.connection.fetchval(
                "SELECT izvorni_podaci  AS raw_data FROM izvorni_zapisi WHERE id=$1",
                record,
            ),
            {},
        )
        await self.load(calls=[CALL], valid_until=None)
        [dates] = await self.connection.fetch(
            "SELECT id_izvornog_zapisa AS source_record_id,referentni_datum AS reference_date,vrsta_datuma AS date_kind,vrijedi_do AS valid_until FROM zapisi_dokumenata"
        )
        self.assertEqual(
            dict(dates),
            {
                "source_record_id": record,
                "reference_date": date(2026, 5, 11),
                "date_kind": "published",
                "valid_until": None,
            },
        )
        before = (await self.rag.retrieve(self.query)).model_dump()

        await self.connection.execute(
            "UPDATE izvorni_zapisi SET izvorni_podaci=$2 WHERE id=$1",
            record,
            {
                "kind": "other",
                "scope": "institution",
                "reference_date": "invalid",
                "date_kind": "observed",
                "valid_until": "invalid",
                "document_url": "https://example.invalid/wrong",
            },
        )
        self.assertEqual((await self.rag.retrieve(self.query)).model_dump(), before)
        rows = await AsyncpgLocationRepository(self.connection).list_locations(
            LocationQuery(city="Zagreb")
        )
        for row in rows:
            [call] = row["enrolment"]
            self.assertEqual(
                (call["reference_date"], call["date_kind"], call["source_url"]),
                ("2026-05-11", "published", "https://example.invalid/upis.pdf"),
            )

    async def test_document_constraints_and_missing_dates_do_not_offer_evidence(self):
        import asyncpg

        await self.load(calls=[CALL])
        for statement, error in (
            (
                "UPDATE zapisi_dokumenata SET referentni_datum=NULL",
                asyncpg.NotNullViolationError,
            ),
            (
                "UPDATE zapisi_dokumenata SET vrsta_datuma=NULL",
                asyncpg.NotNullViolationError,
            ),
            (
                "UPDATE zapisi_dokumenata SET vrsta_datuma='unknown'",
                asyncpg.CheckViolationError,
            ),
            (
                "UPDATE zapisi_dokumenata SET vrijedi_do=referentni_datum-1",
                asyncpg.CheckViolationError,
            ),
            (
                "UPDATE izvori_podataka SET vrsta='unsupported'",
                asyncpg.CheckViolationError,
            ),
        ):
            with self.subTest(statement=statement), self.assertRaises(error):
                async with self.connection.transaction():
                    await self.connection.execute(statement)
        await self.connection.execute("DELETE FROM zapisi_dokumenata")
        self.assertEqual((await self.rag.retrieve(self.query)).status, "no_evidence")
        rows = await AsyncpgLocationRepository(self.connection).list_locations(
            LocationQuery(city="Zagreb")
        )
        self.assertTrue(all(not row["enrolment"] for row in rows))

    async def test_unresolved_names_and_other_provider_kinds_are_rejected(self):
        with self.assertRaisesRegex(SourceImportError, "0 active institutions"):
            await self.load(
                excerpts=[
                    {"content": "Upis.", "institutions": ["Dječji vrtić Nepostojeći"]}
                ]
            )
        with self.assertRaisesRegex(SourceImportError, "No active institutions"):
            await self.load(provider_kinds=["private"])
        with self.assertRaisesRegex(SourceImportError, "No active institutions"):
            await self.load(municipality="rijeka")

    async def test_deleting_document_cascades_and_rollback_restores_its_evidence(self):
        await self.load(calls=[{**CALL, "not_accepting": ["Dječji vrtić Primjer"]}])
        tables = (
            "izvorni_zapisi",
            "zapisi_dokumenata",
            "odlomci_znanja",
            "upisni_krugovi",
            "neprihvacanja_upisa",
            "obuhvati_dokumenata",
            "vrtici",
            "objekti",
        )
        before = {
            table: await self.connection.fetch(f"SELECT * FROM {table} ORDER BY 1,2")
            for table in tables
        }
        record = await self.connection.fetchval(
            "SELECT id_izvornog_zapisa  AS source_record_id FROM upisni_krugovi"
        )
        savepoint = self.connection.transaction()
        await savepoint.start()
        try:
            await self.connection.execute(
                "DELETE FROM izvorni_zapisi WHERE id=$1", record
            )
            await self.connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
            self.assertIsNone(
                await self.connection.fetchval(
                    "SELECT id FROM izvorni_zapisi WHERE id=$1", record
                )
            )
            for table in (
                "zapisi_dokumenata",
                "odlomci_znanja",
                "upisni_krugovi",
                "neprihvacanja_upisa",
                "obuhvati_dokumenata",
            ):
                self.assertEqual(
                    await self.connection.fetchval(f"SELECT count(*) FROM {table}"), 0
                )
            for table in ("vrtici", "objekti"):
                self.assertEqual(
                    await self.connection.fetch(f"SELECT * FROM {table} ORDER BY 1,2"),
                    before[table],
                )
        finally:
            await savepoint.rollback()
        for table in tables:
            self.assertEqual(
                await self.connection.fetch(f"SELECT * FROM {table} ORDER BY 1,2"),
                before[table],
            )

    async def test_deleting_round_cascades_only_its_refusals_and_owner_is_protected(
        self,
    ):
        import asyncpg

        await self.load(calls=[{**CALL, "not_accepting": ["Dječji vrtić Primjer"]}])
        owner = await self.connection.fetchval(
            "SELECT id_vrtica  AS kindergarten_id FROM neprihvacanja_upisa"
        )
        with self.assertRaises(asyncpg.ForeignKeyViolationError):
            async with self.connection.transaction():
                await self.connection.execute("DELETE FROM vrtici WHERE id=$1", owner)
        await self.connection.execute("DELETE FROM upisni_krugovi")
        await self.connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM neprihvacanja_upisa"),
            0,
        )
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM obuhvati_dokumenata"),
            1,
        )
        self.assertGreater(
            await self.connection.fetchval("SELECT count(*) FROM odlomci_znanja"), 0
        )

    async def test_reimport_removes_missing_document_groups_through_cascade(self):
        await self.load(
            excerpts=[
                {"content": "Opća obavijest."},
                {
                    "content": "Posebna obavijest.",
                    "institutions": ["Dječji vrtić Primjer"],
                },
            ]
        )
        await self.load(excerpts=[{"content": "Nova opća obavijest."}])
        await self.connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM obuhvati_dokumenata"),
            1,
        )
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM odlomci_znanja"), 1
        )
        self.assertEqual(
            await self.connection.fetchval("SELECT count(*) FROM zapisi_dokumenata"), 1
        )
        [item] = (await self.rag.retrieve(self.query)).evidence
        self.assertEqual(
            (item.content, item.scope), ("Nova opća obavijest.", "municipality")
        )

    async def test_enrolment_records_never_keep_a_dropped_kindergarten_active(self):

        await self.connection.execute(
            "INSERT INTO sjedista_vrtica(id_vrtica,id_jedinice_lokalne_samouprave) SELECT id,(SELECT id FROM jedinice_lokalne_samouprave WHERE kljuc='zagreb') FROM vrtici ON CONFLICT(id_vrtica) DO UPDATE SET id_jedinice_lokalne_samouprave=EXCLUDED.id_jedinice_lokalne_samouprave"
        )
        await self.load()
        await self.connection.execute(
            "UPDATE izvori_podataka SET uvoz_dopusten=false WHERE kljuc_skupa_podataka='directory'"
        )
        with self.assertRaisesRegex(SourceImportError, "No active institutions"):
            await self.load()
        self.assertEqual((await self.rag.retrieve(self.query)).status, "not_found")


if __name__ == "__main__":
    unittest.main()
