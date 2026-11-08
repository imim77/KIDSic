"""Synthetic database fixtures verify document scope and transaction cleanup."""

from pathlib import Path
from uuid import uuid4

import asyncpg
from support.database import DatabaseTestCase

from KIDSic.dao.concrete.asyncpg_kindergarten import AsyncpgKindergartenRepository
from KIDSic.db.uow.asyncpg import AsyncpgUnitOfWork
from KIDSic.exceptions import PersistenceError


class SearchTests(DatabaseTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.repo = AsyncpgKindergartenRepository(self.connection)
        self.source = await self.connection.fetchval(
            "INSERT INTO izvori_podataka(kljuc_skupa_podataka,naslov,izdavac,poveznica,uvoz_dopusten) VALUES ('directory','Directory','Test','https://example.invalid',true) RETURNING id"
        )

    async def record(self, owner, location=None):
        return await self.connection.fetchval(
            "INSERT INTO izvorni_zapisi(id_izvora,kljuc_izvornog_zapisa,izvorni_podaci,id_vrtica,id_objekta,status_povezivanja,metoda_povezivanja) VALUES ($1,$2,'{}',$3,$4,'accepted','manual') RETURNING id",
            self.source,
            str(uuid4()),
            owner,
            location,
        )

    async def chunk(self, owner, location, record, content="Sourced document"):
        await self.connection.execute(
            "INSERT INTO odlomci_znanja(id_vrtica,id_objekta,id_izvornog_zapisa,redni_broj,sadrzaj,poveznica_izvora) VALUES ($1,$2,$3,0,$4,'https://example.invalid/evidence')",
            owner,
            location,
            record,
            content,
        )

    async def test_application_tables_use_croatian_plural_names(self):
        tables = {
            row["tablename"]
            for row in await self.connection.fetch(
                "SELECT tablename FROM pg_tables WHERE schemaname='public'"
            )
        }
        self.assertEqual(
            tables,
            {
                "izvori_podataka",
                "izvorni_zapisi",
                "vrtici",
                "sjedista_vrtica",
                "objekti",
                "jedinice_lokalne_samouprave",
                "pravila_sufinanciranja",
                "upisni_krugovi",
                "neprihvacanja_upisa",
                "obuhvati_dokumenata",
                "zapisi_dokumenata",
                "odlomci_znanja",
                "povijesni_zapisi",
                "alembic_version",
                "spatial_ref_sys",
            },
        )
        columns = {
            row["column_name"]
            for row in await self.connection.fetch("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema='public' AND table_name='objekti'
        """)
        }
        self.assertTrue(
            {"id", "id_vrtica", "naziv", "id_jedinice_lokalne_samouprave"} <= columns
        )

    async def test_column_migration_round_trip_preserves_records_and_views(self):
        migrations = (
            Path(__file__).resolve().parents[1] / "src/KIDSic/db/alembic/versions"
        )
        before = await self.connection.fetchrow(
            "SELECT id,naslov FROM izvori_podataka WHERE id=$1", self.source
        )
        await self.connection.execute(
            (migrations / "0020_croatian_columns_downgrade.sql").read_text()
        )
        previous = await self.connection.fetchrow(
            "SELECT id,title FROM izvori_podataka WHERE id=$1", self.source
        )
        self.assertEqual(tuple(before.values()), tuple(previous.values()))
        await self.connection.execute(
            (migrations / "0020_croatian_columns.sql").read_text()
        )
        self.assertEqual(
            await self.connection.fetchrow(
                "SELECT id,naslov FROM izvori_podataka WHERE id=$1", self.source
            ),
            before,
        )
        self.assertEqual(
            await self.repo.retrieve_context(location_ids=[], kindergarten_ids=[]), []
        )
        with self.assertRaises(asyncpg.UndefinedColumnError):
            async with self.connection.transaction():
                await self.connection.fetchval(
                    "SELECT title FROM izvori_podataka LIMIT 1"
                )

    async def test_context_respects_owner_facility_and_institution_scope(self):
        owner = await self.connection.fetchval(
            "INSERT INTO vrtici(naziv) VALUES ('Selected') RETURNING id"
        )
        other = await self.connection.fetchval(
            "INSERT INTO vrtici(naziv) VALUES ('Other') RETURNING id"
        )

        async def location(kindergarten_id):
            return await self.connection.fetchval(
                "INSERT INTO objekti(id_vrtica,naziv,naselje,kljuc_naselja) VALUES ($1,'Branch','Zagreb','zagreb') RETURNING id",
                kindergarten_id,
            )

        selected, sibling, elsewhere = (
            await location(owner),
            await location(owner),
            await location(other),
        )
        for kindergarten_id, location_id in (
            (owner, selected),
            (owner, sibling),
            (other, elsewhere),
            (owner, None),
        ):
            await self.chunk(
                kindergarten_id,
                location_id,
                await self.record(kindergarten_id, location_id),
            )
        rows = await self.repo.retrieve_context(location_ids=[selected])
        self.assertEqual({r["location_id"] for r in rows}, {selected, None})
        self.assertEqual({r["kindergarten_id"] for r in rows}, {owner})
        self.assertTrue(all(r["source_url"] for r in rows))
        rows = await self.repo.retrieve_context(
            location_ids=[], kindergarten_ids=[owner]
        )
        self.assertEqual([r["location_id"] for r in rows], [None])
        await self.connection.execute(
            "UPDATE izvori_podataka SET uvoz_dopusten=false WHERE id=$1", self.source
        )
        self.assertEqual(await self.repo.retrieve_context(location_ids=[selected]), [])

    async def test_context_rejects_cross_owner_chunks_and_invalid_limits(self):
        owner = await self.connection.fetchval(
            "INSERT INTO vrtici(naziv) VALUES ('Owner') RETURNING id"
        )
        other = await self.connection.fetchval(
            "INSERT INTO vrtici(naziv) VALUES ('Other') RETURNING id"
        )
        record = await self.record(owner)
        await self.chunk(other, None, record)
        self.assertEqual(
            await self.repo.retrieve_context(location_ids=[], kindergarten_ids=[other]),
            [],
        )
        for value in (0, 31, None, True):
            with self.assertRaises(ValueError):
                await self.repo.retrieve_context(location_ids=[], limit=value)

    async def test_driver_errors_cross_the_read_transaction_as_persistence_errors(self):
        before = self.pool.get_size() - self.pool.get_idle_size()
        with self.assertRaises(PersistenceError) as error:
            async with AsyncpgUnitOfWork(self.pool) as work:
                await work.search.retrieve_context(location_ids=["not-a-uuid"])
        self.assertIsInstance(error.exception.__cause__, asyncpg.PostgresError)
        self.assertEqual(self.pool.get_size() - self.pool.get_idle_size(), before)

    async def test_context_excludes_rejected_candidate_and_mismatched_facility_evidence(
        self,
    ):
        owner = await self.connection.fetchval(
            "INSERT INTO vrtici(naziv) VALUES ('Owner') RETURNING id"
        )
        locations = [
            await self.connection.fetchval(
                """INSERT INTO objekti
            (id_vrtica,naziv,naselje,kljuc_naselja)
            VALUES ($1,$2,'Zagreb','zagreb') RETURNING id""",
                owner,
                name,
            )
            for name in ("Selected", "Sibling")
        ]
        selected, sibling = locations
        await self.chunk(owner, selected, await self.record(owner, selected), "Valid")
        inactive = await self.record(owner, selected)
        await self.chunk(owner, selected, inactive, "Inactive")
        await self.connection.execute(
            "UPDATE izvorni_zapisi SET status_povezivanja='rejected' WHERE id=$1",
            inactive,
        )
        candidate = await self.record(owner, selected)
        await self.chunk(owner, selected, candidate, "Candidate")
        await self.connection.execute(
            "UPDATE izvorni_zapisi SET status_povezivanja='candidate' WHERE id=$1",
            candidate,
        )
        await self.chunk(
            owner, selected, await self.record(owner, sibling), "Wrong facility"
        )
        rows = await self.repo.retrieve_context(location_ids=[selected])
        self.assertEqual([row["content"] for row in rows], ["Valid"])

    async def test_unit_of_work_releases_connection_after_error(self):
        before = self.pool.get_size() - self.pool.get_idle_size()
        with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
            async with AsyncpgUnitOfWork(self.pool) as uow:
                await uow.search.retrieve_context(location_ids=[])
                raise RuntimeError("synthetic failure")
        self.assertEqual(self.pool.get_size() - self.pool.get_idle_size(), before)
        async with AsyncpgUnitOfWork(self.pool) as uow:
            self.assertIsInstance(
                await uow.search.retrieve_context(location_ids=[]), list
            )
