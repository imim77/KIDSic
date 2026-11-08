"""Subsidy seed verifies persistence and keeps unconfirmed amounts unknown."""

from pathlib import Path

import asyncpg
from support.database import DatabaseTestCase

from KIDSic.dao.concrete.asyncpg_location import AsyncpgLocationRepository
from KIDSic.dto.location import LocationQuery


class SubsidyDatabaseTests(DatabaseTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        for key in ("zagreb", "varazdin", "rijeka"):
            await self.connection.execute(
                "INSERT INTO jedinice_lokalne_samouprave(kljuc,naziv) VALUES ($1,$1) ON CONFLICT (kljuc) DO NOTHING",
                key,
            )
        sql = (
            Path(__file__).resolve().parents[1] / "src/KIDSic/db/seeds/"
            "2026-11-04_municipal_subsidies.sql"
        ).read_text()
        # Keep the production seed inside the fixture's rollback transaction.
        self.seed = sql.replace("\nBEGIN;\n", "\n").replace("\nCOMMIT;\n", "\n")

    async def test_seed_replays_without_changing_facilities_or_policy_identities(self):
        before = await self.connection.fetch("SELECT id FROM vrtici ORDER BY id")
        await self.connection.execute(self.seed)
        policies = await self.connection.fetch(
            "SELECT id,kljuc_pravila AS policy_key,id_jedinice_lokalne_samouprave AS municipality_id,vrste_pruzatelja AS provider_kinds,naslov AS title,sazetak AS summary,status_provjere AS verification_status,datum_provjere AS verified_on,vrijedi_od AS valid_from,vrijedi_do AS valid_until,pravila AS rules,izvori AS sources FROM pravila_sufinanciranja ORDER BY kljuc_pravila"
        )
        self.assertEqual(len(policies), 9)
        await self.connection.execute(self.seed)
        self.assertEqual(
            policies,
            await self.connection.fetch(
                "SELECT id,kljuc_pravila AS policy_key,id_jedinice_lokalne_samouprave AS municipality_id,vrste_pruzatelja AS provider_kinds,naslov AS title,sazetak AS summary,status_provjere AS verification_status,datum_provjere AS verified_on,vrijedi_od AS valid_from,vrijedi_do AS valid_until,pravila AS rules,izvori AS sources FROM pravila_sufinanciranja ORDER BY kljuc_pravila"
            ),
        )
        self.assertEqual(
            before, await self.connection.fetch("SELECT id FROM vrtici ORDER BY id")
        )
        self.assertEqual(
            await self.connection.fetchval(
                "SELECT count(*) FROM pravila_sufinanciranja WHERE 'unknown'=ANY(vrste_pruzatelja) OR 'other'=ANY(vrste_pruzatelja)"
            ),
            0,
        )
        rows = {row["policy_key"]: row for row in policies}
        childminder = rows["varazdin-childminder-20261104"]
        self.assertEqual(childminder["verification_status"], "partial")
        self.assertIsNone(childminder["rules"]["city_subsidy_cents"])
        rijeka = rows["rijeka-childminder-20261104"]["rules"]
        self.assertEqual(rijeka["rates"][0]["city_subsidy_cents"], 26000)
        self.assertEqual(rijeka["pending_change"]["status"], "consultation_not_adopted")
        zagreb = rows["zagreb-private-20261104"]["rules"]
        for rate in zagreb["rates"]:
            self.assertEqual(
                rate["city_subsidy_cents"],
                rate["base_city_subsidy_cents"] + rate["fixed_city_top_up_cents"],
            )
        self.assertIsNone(
            rows["zagreb-municipal-20261104"]["rules"]["city_subsidy_cents"]
        )

    async def test_missing_city_rolls_back_seed_and_invalid_types_are_rejected(self):
        with self.assertRaises(asyncpg.NotNullViolationError):
            async with self.connection.transaction():
                await self.connection.execute(
                    self.seed.replace(
                        '"municipality_key": "rijeka"', '"municipality_key": "missing"'
                    )
                )
        self.assertEqual(
            await self.connection.fetchval(
                "SELECT count(*) FROM pravila_sufinanciranja"
            ),
            0,
        )
        await self.connection.execute(self.seed)
        with self.assertRaises(asyncpg.CheckViolationError):
            async with self.connection.transaction():
                await self.connection.execute(
                    "UPDATE pravila_sufinanciranja SET vrste_pruzatelja=ARRAY['unknown']"
                )

    async def test_location_uses_facility_city_and_type_and_excludes_inactive_periods(
        self,
    ):
        await self.connection.execute(self.seed)
        cities = {
            r["key"]: r["id"]
            for r in await self.connection.fetch(
                "SELECT kljuc AS key,id FROM jedinice_lokalne_samouprave"
            )
        }
        source = await self.connection.fetchval("""INSERT INTO izvori_podataka
            (kljuc_skupa_podataka,naslov,izdavac,poveznica,uvoz_dopusten)
            VALUES ('subsidy-test','Test','Test','https://example.invalid',true) RETURNING id""")
        for kind in ("private", "unknown"):
            owner = await self.connection.fetchval(
                """INSERT INTO vrtici
                (naziv,vrsta_pruzatelja) VALUES ('Test',$1) RETURNING id""",
                kind,
            )
            await self.connection.execute(
                "INSERT INTO sjedista_vrtica(id_vrtica,id_jedinice_lokalne_samouprave) VALUES ($1,$2)",
                owner,
                cities["zagreb"],
            )
            location = await self.connection.fetchval(
                """INSERT INTO objekti
                (id_vrtica,naziv,naselje,kljuc_naselja,id_jedinice_lokalne_samouprave)
                VALUES ($1,'Rijeka branch','Rijeka','rijeka',$2) RETURNING id""",
                owner,
                cities["rijeka"],
            )
            await self.connection.execute(
                """INSERT INTO izvorni_zapisi
                (id_izvora,izvorni_podaci,id_vrtica,id_objekta,status_povezivanja,metoda_povezivanja)
                VALUES ($1,'{}',$2,$3,'accepted','manual')""",
                source,
                owner,
                location,
            )
        repo = AsyncpgLocationRepository(self.connection)
        rows = await repo.list_locations(LocationQuery(city="Rijeka"))
        private = next(r for r in rows if r["provider_kind"] == "private")
        self.assertEqual(
            [p["policy_key"] for p in private["subsidy_policies"]],
            ["rijeka-private-20261104"],
        )
        self.assertEqual(
            next(r for r in rows if r["provider_kind"] == "unknown")[
                "subsidy_policies"
            ],
            [],
        )
        await self.connection.execute("""UPDATE pravila_sufinanciranja
            SET vrijedi_do=CURRENT_DATE-1 WHERE kljuc_pravila='rijeka-private-20261104'""")
        self.assertTrue(
            all(
                not r["subsidy_policies"]
                for r in await repo.list_locations(LocationQuery(city="Rijeka"))
            )
        )
        await self.connection.execute("""UPDATE pravila_sufinanciranja
            SET vrijedi_od=CURRENT_DATE+1,vrijedi_do=NULL WHERE kljuc_pravila='rijeka-private-20261104'""")
        self.assertTrue(
            all(
                not r["subsidy_policies"]
                for r in await repo.list_locations(LocationQuery(city="Rijeka"))
            )
        )
