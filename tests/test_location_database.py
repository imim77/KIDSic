"""Rollback-only location integration fixtures are synthetic, never real institutions."""

from datetime import UTC, datetime
from uuid import uuid4

from support.database import DatabaseTestCase

from KIDSic.dao.concrete.asyncpg_location import AsyncpgLocationRepository
from KIDSic.dao.concrete.asyncpg_source import AsyncpgSourceRepository
from KIDSic.dto.location import LocationQuery
from KIDSic.dto.source import PlannedSource, SourceDefinition, SourceSnapshot
from KIDSic.services.concrete.kindergarten_normalizer import normalize_records


class LocationDatabaseTests(DatabaseTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.repository = AsyncpgLocationRepository(self.connection)
        self.source = await self.connection.fetchval(
            """INSERT INTO izvori_podataka
            (kljuc_skupa_podataka,naslov,izdavac,poveznica,licenca,uvoz_dopusten)
            VALUES ($1,'Synthetic','Test','https://example.invalid','Test license',true)
            RETURNING id""",
            str(uuid4()),
        )
        self.municipality = await self.connection.fetchval("""INSERT INTO jedinice_lokalne_samouprave(kljuc,naziv,alternativni_nazivi)
            VALUES ('zagreb','Zagreb','{zagreba}') ON CONFLICT (kljuc)
            DO UPDATE SET alternativni_nazivi=EXCLUDED.alternativni_nazivi RETURNING id""")

    async def fixture(
        self,
        name="Synthetic",
        *,
        city="Zagreb",
        provider="municipal",
        coords=(15.98, 45.81),
        active=True,
        seat=False,
    ):
        institution = await self.connection.fetchval(
            """INSERT INTO vrtici
            (naziv,vrsta_pruzatelja) VALUES ($1,$2) RETURNING id""",
            name,
            provider,
        )
        await self.connection.execute(
            "INSERT INTO sjedista_vrtica(id_vrtica,adresa,naselje,kljuc_naselja) VALUES ($1,'Seat 1','Zagreb','zagreb')",
            institution,
        )
        location = None
        if not seat:
            location = await self.connection.fetchval(
                """INSERT INTO objekti
                (id_vrtica,naziv,naselje,kljuc_naselja,id_jedinice_lokalne_samouprave,geografska_duzina,geografska_sirina)
                VALUES ($1,$2,$3,lower($3),$4,$5,$6) RETURNING id""",
                institution,
                name + " branch",
                city,
                self.municipality if city == "Sesvete" else None,
                *coords,
            )
        await self.record(institution, location, active=active)
        return institution, location

    async def record(self, institution, location, *, active=True, source=None):
        await self.connection.execute(
            """INSERT INTO izvorni_zapisi
            (id_izvora,izvorni_podaci,id_vrtica,id_objekta,status_povezivanja,metoda_povezivanja,
             datum_opazanja,dohvaceno_u)
            VALUES ($1,'{}',$2,$3,$4,'new','2026-10-01','2026-11-02T10:00Z')""",
            source or self.source,
            institution,
            location,
            "accepted" if active else "rejected",
        )

    async def test_rag_contact_provenance_cannot_cite_a_sibling_or_disabled_record(
        self,
    ):
        owner, location = await self.fixture("Contacts")
        sibling = await self.connection.fetchval(
            "INSERT INTO objekti(id_vrtica,naziv,naselje,kljuc_naselja) VALUES($1,'Sibling','Zagreb','zagreb') RETURNING id",
            owner,
        )
        await self.record(owner, sibling)
        record = await self.connection.fetchval(
            "SELECT id FROM izvorni_zapisi WHERE id_objekta=$1", sibling
        )
        await self.connection.execute(
            "UPDATE vrtici SET e_posta=$2,podrijetlo=$3 WHERE id=$1",
            owner,
            "branch@example.invalid",
            {"email": {"source_record_id": str(record)}},
        )
        rows = await self.repository.list_locations(LocationQuery())
        selected = next(r for r in rows if r["location_id"] == location)
        related = next(r for r in rows if r["location_id"] == sibling)
        self.assertIsNone(selected["contact_sources"]["email"])
        self.assertEqual(related["contact_sources"]["email"]["scope"], "facility")
        await self.connection.execute(
            "UPDATE izvorni_zapisi SET status_povezivanja='candidate' WHERE id=$1",
            record,
        )
        rows = await self.repository.list_locations(LocationQuery())
        self.assertTrue(all(r["contact_sources"]["email"] is None for r in rows))

    async def test_accepted_records_and_deduplication_keep_source_dates(self):
        institution, location = await self.fixture()
        await self.record(institution, location)
        second = await self.connection.fetchval(
            """INSERT INTO izvori_podataka
            (kljuc_skupa_podataka,naslov,izdavac,poveznica,uvoz_dopusten)
            VALUES ($1,'Second','Test','https://example.invalid/second',true)
            RETURNING id""",
            str(uuid4()),
        )
        await self.record(institution, location, source=second)
        await self.fixture("Inactive", active=False)
        for status in ("candidate", "rejected"):
            ignored, _ = await self.fixture(status)
            await self.connection.execute(
                "UPDATE izvorni_zapisi SET status_povezivanja=$2 WHERE id_vrtica=$1",
                ignored,
                status,
            )
        rows = await self.repository.list_locations(LocationQuery())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["location_id"], location)
        self.assertEqual(len(rows[0]["sources"]), 2)
        self.assertEqual(rows[0]["sources"][1]["reference_date"], "2026-10-01")
        self.assertTrue(all(source["retrieved_at"] for source in rows[0]["sources"]))
        await self.connection.execute(
            "UPDATE izvori_podataka SET uvoz_dopusten=false WHERE id=$1", second
        )
        self.assertEqual(
            len((await self.repository.list_locations(LocationQuery()))[0]["sources"]),
            1,
        )
        await self.connection.execute(
            "UPDATE izvori_podataka SET uvoz_dopusten=false WHERE id=$1", self.source
        )
        self.assertEqual(await self.repository.list_locations(LocationQuery()), [])

    async def test_contacts_prefer_the_active_facility_then_reviewed_phone_and_institution(
        self,
    ):
        owner, location = await self.fixture("Contact owner")
        await self.connection.execute(
            """UPDATE vrtici SET mrezna_stranica='https://example.invalid/owner',
            e_posta='owner@example.invalid',telefon='01/111-1111' WHERE id=$1""",
            owner,
        )
        await self.connection.execute(
            "UPDATE izvorni_zapisi SET izvorni_podaci=$2 WHERE id_objekta=$1",
            location,
            {
                "Web": " https://example.invalid/branch ",
                "Email": " branch@example.invalid ",
                "Telefon": " 01/222-2222 ",
            },
        )
        branch = await self.connection.fetchval(
            """INSERT INTO objekti
            (id_vrtica,naziv,naselje,kljuc_naselja,obiljezja)
            VALUES ($1,'Second branch','Zagreb','zagreb',$2) RETURNING id""",
            owner,
            {"phone": "01/333-3333"},
        )
        await self.record(owner, branch)
        rows = {
            r["location_id"]: r
            for r in await self.repository.list_locations(LocationQuery())
        }
        self.assertEqual(
            tuple(rows[location][key] for key in ("website_url", "email", "phone")),
            ("https://example.invalid/branch", "branch@example.invalid", "01/222-2222"),
        )
        self.assertEqual(
            tuple(rows[branch][key] for key in ("website_url", "email", "phone")),
            ("https://example.invalid/owner", "owner@example.invalid", "01/333-3333"),
        )
        # A rejected contact cannot override the currently available fallback.
        await self.connection.execute(
            "UPDATE izvorni_zapisi SET status_povezivanja='rejected' WHERE id_objekta=$1",
            location,
        )
        await self.record(owner, location)
        rows = {
            r["location_id"]: r
            for r in await self.repository.list_locations(LocationQuery())
        }
        self.assertEqual(rows[location]["email"], "owner@example.invalid")
        seat, _ = await self.fixture("Seat contact", seat=True)
        await self.connection.execute(
            "UPDATE vrtici SET e_posta='seat@example.invalid',telefon=' ' WHERE id=$1",
            seat,
        )
        rows = await self.repository.list_locations(LocationQuery(q="Seat contact"))
        self.assertEqual(rows[0]["email"], "seat@example.invalid")
        self.assertIsNone(rows[0]["phone"])
        self.assertIsNone(rows[0]["website_url"])

    async def test_seat_geography_requires_current_address_and_approved_evidence(self):
        from KIDSic.dao.concrete.asyncpg_kindergarten import (
            AsyncpgKindergartenRepository,
        )

        owner, _ = await self.fixture(
            "Childminder seat", provider="childminder", seat=True
        )
        geo_source = await self.connection.fetchval(
            "INSERT INTO izvori_podataka(kljuc_skupa_podataka,naslov,izdavac,poveznica,uvoz_dopusten) VALUES ($1,'Geo','Test','https://example.invalid/geo',true) RETURNING id",
            str(uuid4()),
        )
        record = await self.connection.fetchval(
            "INSERT INTO izvorni_zapisi(id_izvora,izvorni_podaci,id_vrtica,status_povezivanja,metoda_povezivanja) VALUES ($1,'{}',$2,'accepted','manual') RETURNING id",
            geo_source,
            owner,
        )
        await self.connection.execute(
            "UPDATE sjedista_vrtica SET geografska_duzina=15.98,geografska_sirina=45.81,obiljezja=$2,id_zapisa_geografskog_izvora=$3 WHERE id_vrtica=$1",
            owner,
            {
                "address": "Seat 1",
                "quarter": "Synthetic quarter",
                "suburb": "Banfica",
                "neighbourhood": "Synthetic neighbourhood",
                "settlement": "Zagreb",
            },
            record,
        )
        await self.connection.execute(
            "UPDATE izvorni_zapisi SET izvorni_podaci=$2 WHERE id=$1",
            record,
            {"evidence_scope": "registered_seat_geography"},
        )
        await self.connection.execute(
            "INSERT INTO odlomci_znanja(id_vrtica,id_izvornog_zapisa,redni_broj,sadrzaj,poveznica_izvora) VALUES ($1,$2,0,'Banfica seat geography','https://example.invalid/geo')",
            owner,
            record,
        )
        rows = await self.repository.list_locations(LocationQuery())
        self.assertEqual(
            (rows[0]["location_id"], rows[0]["location_role"], rows[0]["longitude"]),
            (None, "seat", 15.98),
        )
        self.assertIn("longitude", rows[0]["field_sources"])
        self.assertIn("Banfica", rows[0]["areas"])
        self.assertEqual(
            len(await self.repository.list_locations(LocationQuery(area="banfica"))), 1
        )
        search = AsyncpgKindergartenRepository(self.connection)
        self.assertEqual(
            len(
                await search.retrieve_context(location_ids=[], kindergarten_ids=[owner])
            ),
            1,
        )
        await self.connection.execute(
            "UPDATE izvori_podataka SET uvoz_dopusten=false WHERE id=$1", geo_source
        )
        self.assertIsNone(
            (await self.repository.list_locations(LocationQuery()))[0]["longitude"]
        )
        self.assertEqual(
            await self.repository.list_locations(LocationQuery(area="Banfica")), []
        )
        await self.connection.execute(
            "UPDATE izvori_podataka SET uvoz_dopusten=true WHERE id=$1", geo_source
        )
        await self.connection.execute(
            "UPDATE sjedista_vrtica SET adresa='New seat 2' WHERE id_vrtica=$1", owner
        )
        self.assertEqual(
            await self.repository.list_locations(LocationQuery(area="Banfica")), []
        )
        self.assertIsNone(
            (await self.repository.list_locations(LocationQuery()))[0]["longitude"]
        )
        self.assertEqual(
            await search.retrieve_context(location_ids=[], kindergarten_ids=[owner]), []
        )
        self.assertEqual(
            await self.repository.list_locations(LocationQuery(bbox=(15, 45, 16, 46))),
            [],
        )
        # The FK rejects missing records; an existing sibling owner's proof is
        # also excluded by the geography view's ownership check.
        import asyncpg

        with self.assertRaises(asyncpg.ForeignKeyViolationError):
            async with self.connection.transaction():
                await self.connection.execute(
                    "UPDATE sjedista_vrtica SET id_zapisa_geografskog_izvora=$2 WHERE id_vrtica=$1",
                    owner,
                    uuid4(),
                )
        other = await self.connection.fetchval(
            "INSERT INTO vrtici(naziv) VALUES ('Other owner') RETURNING id"
        )
        other_record = await self.connection.fetchval(
            "INSERT INTO izvorni_zapisi(id_izvora,izvorni_podaci,id_vrtica,status_povezivanja,metoda_povezivanja) VALUES ($1,'{}',$2,'accepted','manual') RETURNING id",
            geo_source,
            other,
        )
        await self.connection.execute(
            "UPDATE sjedista_vrtica SET adresa='Seat 1',id_zapisa_geografskog_izvora=$2 WHERE id_vrtica=$1",
            owner,
            other_record,
        )
        self.assertIsNone(
            (await self.repository.list_locations(LocationQuery()))[0]["longitude"]
        )

    async def test_seat_fallback_and_unlocated_facility_stay_distinct(self):
        seat, _ = await self.fixture("Seat only", seat=True)
        unlocated, _ = await self.fixture("Unlocated", coords=(None, None))
        outside, _ = await self.fixture("Outside", city="Other town")
        rows = await self.repository.list_locations(LocationQuery())
        self.assertEqual({r["kindergarten_id"] for r in rows}, {seat, unlocated})
        self.assertEqual({r["location_role"] for r in rows}, {"seat", "facility"})
        self.assertTrue(all(r["longitude"] is None for r in rows))
        self.assertNotIn(outside, [r["kindergarten_id"] for r in rows])
        self.assertEqual(
            await self.repository.list_locations(LocationQuery(bbox=(15, 45, 16, 46))),
            [],
        )

    async def test_municipality_name_literal_query_provider_and_inclusive_bbox(self):
        _, location = await self.fixture(
            "100% Medo", city="Sesvete", provider="private"
        )
        await self.fixture("Other municipal")
        query = LocationQuery(
            city="zagreba",
            q="100%",
            provider_kind="private",
            bbox=(15.98, 45.81, 16, 46),
        )
        self.assertEqual(
            [r["location_id"] for r in await self.repository.list_locations(query)],
            [location],
        )
        self.assertEqual(
            await self.repository.list_locations(LocationQuery(q="missing")), []
        )
        with self.assertRaises(ValueError):
            LocationQuery(city="Split")

    async def vacancies(self, owner, date, *places):
        await self.connection.execute(
            """INSERT INTO povijesni_zapisi
            (id_izvora,kljuc_izvornog_zapisa,izvorni_podaci,id_vrtica,obuhvat,status_povezivanja,
             referentni_datum,vrsta_datuma,dohvaceno_u,slobodna_mjesta)
            VALUES ($1,$2,'{}',$3,'institution','accepted',$4,'observed','2026-11-02T10:00Z',$5)""",
            self.source,
            str(uuid4()),
            owner,
            date,
            [
                {"age_label": "od 1 godine do OŠ", "program": None, "free_places": n}
                for n in places
            ],
        )

    async def test_vacancy_filter_uses_the_newest_published_snapshot(self):
        from datetime import date

        free, free_loc = await self.fixture("Free")
        await self.vacancies(free, date(2025, 1, 1), 0, 2)
        zero, _ = await self.fixture("Zero")
        await self.vacancies(zero, date(2025, 1, 1), 0)
        await self.fixture("Unpublished")
        # A newer published zero replaces an older positive count.
        filled, _ = await self.fixture("Filled")
        await self.vacancies(filled, date(2024, 1, 1), 5)
        await self.vacancies(filled, date(2025, 1, 1), 0)
        unknown, _ = await self.fixture("Unknown")
        await self.vacancies(unknown, date(2025, 1, 1), None)
        rows = await self.repository.list_locations(LocationQuery(has_vacancies=True))
        self.assertEqual([r["location_id"] for r in rows], [free_loc])
        self.assertEqual(len(await self.repository.list_locations(LocationQuery())), 5)

    async def test_radius_keeps_only_verified_points_and_reports_metres(self):
        # 0.01° latitude is about 1112 m on the spheroid.
        _, centre = await self.fixture("Centre", coords=(15.98, 45.81))
        _, near = await self.fixture("Near", coords=(15.98, 45.82))
        # Alphabetically first but farther than Centre: distance must win over name.
        _, alpha = await self.fixture("Alpha", coords=(15.98, 45.817))
        await self.fixture("Far", coords=(15.98, 45.85))
        await self.fixture("Unlocated", coords=(None, None))
        await self.fixture("Seat only", seat=True)
        rows = await self.repository.list_locations(
            LocationQuery(near=(15.98, 45.81), radius_m=1200)
        )
        self.assertEqual(
            [(r["location_id"], r["distance_m"]) for r in rows],
            [
                (centre, 0),
                (alpha, rows[1]["distance_m"]),
                (near, rows[2]["distance_m"]),
            ],
        )
        self.assertTrue(770 <= rows[1]["distance_m"] <= 790)
        self.assertTrue(1100 <= rows[2]["distance_m"] <= 1120)
        self.assertEqual(
            [
                r["location_id"]
                for r in await self.repository.list_locations(
                    LocationQuery(near=(15.98, 45.81), radius_m=1000)
                )
            ],
            [centre, alpha],
        )
        self.assertTrue(
            all(
                r["distance_m"] is None
                for r in await self.repository.list_locations(LocationQuery())
            )
        )

    async def test_complete_city_has_no_recommendation_limit(self):
        for i in range(101):
            await self.fixture(f"Facility {i}")
        self.assertEqual(
            len(await self.repository.list_locations(LocationQuery())), 101
        )
        rows = await self.repository.list_locations(LocationQuery())
        self.assertEqual(len(rows), 101)

    async def test_all_provider_types_filter_exactly_with_city_name_and_unmapped_locations(
        self,
    ):
        kinds = ("municipal", "private", "religious", "childminder", "other", "unknown")
        expected = {}
        for kind in kinds:
            _, expected[kind] = await self.fixture(
                "Bajka " + kind,
                provider=kind,
                coords=(None, None)
                if kind in ("childminder", "unknown")
                else (15.98, 45.81),
            )
        await self.fixture("Bajka outside city", city="Rijeka", provider="private")
        await self.fixture("Other name", provider="private")
        for kind in kinds:
            rows = await self.repository.list_locations(
                LocationQuery(city="Zagreb", q="Bajka", provider_kind=kind)
            )
            self.assertEqual([r["location_id"] for r in rows], [expected[kind]])
            self.assertEqual({r["provider_kind"] for r in rows}, {kind})
            self.assertEqual(
                await self.repository.list_locations(
                    LocationQuery(
                        city="Zagreb", q="No matching name", provider_kind=kind
                    )
                ),
                [],
            )
        rows = await self.repository.list_locations(
            LocationQuery(city="Zagreb", q="Bajka")
        )
        self.assertEqual({r["location_id"] for r in rows}, set(expected.values()))

    async def test_area_filters_attested_fields_exactly_and_combines_with_other_filters(
        self,
    ):
        expected = []
        for field in ("district", "quarter", "suburb", "neighbourhood", "settlement"):
            _, location = await self.fixture(
                "Bajka " + field, provider="private", coords=(None, None)
            )
            if field == "district":
                await self.connection.execute(
                    "UPDATE objekti SET gradska_cetvrt='Črnomerec' WHERE id=$1",
                    location,
                )
            elif field == "settlement":
                await self.connection.execute(
                    "UPDATE objekti SET naselje='Črnomerec',kljuc_naselja='crnomerec',id_jedinice_lokalne_samouprave=$2 WHERE id=$1",
                    location,
                    self.municipality,
                )
            else:
                await self.connection.execute(
                    "UPDATE objekti SET obiljezja=$2 WHERE id=$1",
                    location,
                    {field: "Črnomerec"},
                )
            expected.append(location)
        _, wrong_type = await self.fixture("Bajka municipal")
        await self.connection.execute(
            "UPDATE objekti SET gradska_cetvrt='Črnomerec' WHERE id=$1", wrong_type
        )
        await self.fixture("Črnomerec name only", provider="private")
        _, address_only = await self.fixture("Bajka address", provider="private")
        await self.connection.execute(
            "UPDATE objekti SET adresa='Črnomerec 1' WHERE id=$1", address_only
        )
        _, wrong_city = await self.fixture(
            "Bajka Rijeka", city="Rijeka", provider="private"
        )
        await self.connection.execute(
            "UPDATE objekti SET gradska_cetvrt='Črnomerec' WHERE id=$1", wrong_city
        )
        for area in ("Črnomerec", " CRNOMEREC "):
            rows = await self.repository.list_locations(
                LocationQuery(
                    city="Zagreb", q="Bajka", provider_kind="private", area=area
                )
            )
            self.assertEqual({r["location_id"] for r in rows}, set(expected))
            self.assertTrue(
                all("Črnomerec" in r["areas"] and r["longitude"] is None for r in rows)
            )
        for area in ("Črno", "%", "' OR 1=1 --", "Missing area"):
            self.assertEqual(
                await self.repository.list_locations(LocationQuery(area=area)), []
            )
        self.assertEqual(
            len(await self.repository.list_locations(LocationQuery(area="   "))), 8
        )
        self.assertEqual(
            await self.repository.list_locations(
                LocationQuery(city="Zagrebu", area="Zagreb")
            ),
            [],
        )
        await self.connection.execute(
            "UPDATE objekti SET obiljezja=$2 WHERE id=$1",
            expected[1],
            {"quarter": "Mjesni odbor Zamet"},
        )
        for area in ("Zamet", "mjesni odbor ZAMET"):
            self.assertEqual(
                [
                    r["location_id"]
                    for r in await self.repository.list_locations(
                        LocationQuery(area=area)
                    )
                ],
                [expected[1]],
            )

    async def test_area_evidence_must_be_current_allowed_and_belong_to_exact_object(
        self,
    ):
        owner, location = await self.fixture("Target")
        record = await self.connection.fetchval(
            "SELECT id FROM izvorni_zapisi WHERE id_objekta=$1", location
        )
        _, other_location = await self.fixture("Other")
        other_record = await self.connection.fetchval(
            "SELECT id FROM izvorni_zapisi WHERE id_objekta=$1", other_location
        )
        sibling = await self.connection.fetchval(
            "INSERT INTO objekti(id_vrtica,naziv,naselje,kljuc_naselja) VALUES ($1,'Sibling','Zagreb','zagreb') RETURNING id",
            owner,
        )
        await self.record(owner, sibling)
        sibling_record = await self.connection.fetchval(
            "SELECT id FROM izvorni_zapisi WHERE id_objekta=$1", sibling
        )
        alternate = await self.connection.fetchval(
            "INSERT INTO izvori_podataka(kljuc_skupa_podataka,naslov,izdavac,poveznica,uvoz_dopusten) VALUES ($1,'Current','Test','https://example.invalid/current',true) RETURNING id",
            str(uuid4()),
        )
        await self.record(owner, location, source=alternate)
        await self.connection.execute(
            "UPDATE objekti SET gradska_cetvrt='Banfica',obiljezja=$2 WHERE id=$1",
            location,
            {"quarter": "Banfica", "suburb": "Banfica", "neighbourhood": "Banfica"},
        )
        for pointer, status, allowed in (
            (record, "accepted", True),
            (record, "rejected", True),
            (record, "candidate", True),
            (record, "accepted", False),
            (other_record, "accepted", True),
            (sibling_record, "accepted", True),
            (uuid4(), "accepted", True),
        ):
            await self.connection.execute(
                "UPDATE izvorni_zapisi SET status_povezivanja=$2 WHERE id=$1",
                record,
                status,
            )
            await self.connection.execute(
                "UPDATE izvori_podataka SET uvoz_dopusten=$2 WHERE id=$1",
                self.source,
                allowed,
            )
            await self.connection.execute(
                "UPDATE objekti SET podrijetlo=$2 WHERE id=$1",
                location,
                {
                    key: {"source_record_id": str(pointer)}
                    for key in ("district", "quarter", "suburb", "neighbourhood")
                },
            )
            rows = await self.repository.list_locations(
                LocationQuery(q="Target", area="Banfica")
            )
            valid = pointer == record and status == "accepted" and allowed
            self.assertEqual(
                [r["location_id"] for r in rows], [location] if valid else []
            )
            unfiltered = await self.repository.list_locations(LocationQuery(q="Target"))
            self.assertIn(location, [r["location_id"] for r in unfiltered])

    async def test_name_search_matches_parent_and_branch_with_croatian_letters_and_city_scope(
        self,
    ):
        _, branch = await self.fixture("Dječji vrtić Čarobna kućica")
        await self.connection.execute(
            "UPDATE objekti SET naziv='Đački kutak' WHERE id=$1", branch
        )
        await self.fixture("Dječji vrtić Čarobna kućica", city="Rijeka")
        await self.fixture("Other")
        for query in ("ČAROBNA", "carobna", "kućica", "KUCICA", "Đački", "dacki"):
            with self.subTest(query=query):
                rows = await self.repository.list_locations(
                    LocationQuery(city="Zagreb", q=query)
                )
                self.assertEqual([r["location_id"] for r in rows], [branch])
        self.assertEqual(
            await self.repository.list_locations(LocationQuery(q="%' OR 1=1 --")), []
        )

    async def test_reimport_clears_coordinates_missing_from_current_source(self):
        from support.sources import MUNICIPAL, source_client

        client = source_client("municipal")
        package = client.get_package.return_value
        source = PlannedSource(
            SourceDefinition(
                "coordinate-history",
                "https://data.zagreb.hr",
                "gradski_vrtici_grada_zagreba",
                "municipal",
            ),
            package,
            package.resources[0],
        )
        importer = AsyncpgSourceRepository(self.connection)
        earlier = datetime(2026, 10, 1, tzinfo=UTC)
        current = datetime(2026, 11, 1, tzinfo=UTC)
        await importer.import_snapshot(
            SourceSnapshot(source, normalize_records([MUNICIPAL], "municipal"), earlier)
        )
        await importer.import_snapshot(
            SourceSnapshot(
                source,
                normalize_records(
                    [{**MUNICIPAL, "X": None, "Y": None, "GradskaCetvrt": None}],
                    "municipal",
                ),
                current,
            )
        )
        rows = await self.repository.list_locations(LocationQuery())
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["longitude"], rows[0]["latitude"]), (None, None))
        fields = rows[0]["field_sources"]
        for field in ("longitude", "latitude", "district"):
            self.assertNotIn(field, fields)
        self.assertNotIn("active_snapshot", fields["address"])
        self.assertEqual(
            datetime.fromisoformat(fields["address"]["retrieved_at"]), current
        )
        self.assertEqual(
            datetime.fromisoformat(rows[0]["sources"][0]["retrieved_at"]), current
        )

    async def test_invalid_coordinate_provenance_keeps_list_entry_but_excludes_point_and_bbox(
        self,
    ):
        owner, location = await self.fixture("Target")
        evidence = await self.connection.fetchval(
            "SELECT id FROM izvorni_zapisi WHERE id_objekta=$1", location
        )
        alternate = await self.connection.fetchval(
            """INSERT INTO izvori_podataka
            (kljuc_skupa_podataka,naslov,izdavac,poveznica,uvoz_dopusten)
            VALUES ($1,'Current','Test','https://example.invalid/current',true)
            RETURNING id""",
            str(uuid4()),
        )
        await self.record(owner, location, source=alternate)
        _, other_location = await self.fixture("Other")
        wrong_owner = await self.connection.fetchval(
            "SELECT id FROM izvorni_zapisi WHERE id_objekta=$1", other_location
        )
        same_owner_location = await self.connection.fetchval(
            """INSERT INTO objekti
            (id_vrtica,naziv,naselje,kljuc_naselja)
            VALUES ($1,'Other branch','Zagreb','zagreb') RETURNING id""",
            owner,
        )
        await self.record(owner, same_owner_location, active=False)
        wrong_location = await self.connection.fetchval(
            "SELECT id FROM izvorni_zapisi WHERE id_objekta=$1", same_owner_location
        )
        for label, pointer, status, allowed in (
            ("rejected", evidence, "rejected", True),
            ("candidate", evidence, "candidate", True),
            ("wrong_owner", wrong_owner, "accepted", True),
            ("wrong_location", wrong_location, "accepted", True),
            ("disabled", evidence, "accepted", False),
        ):
            with self.subTest(label=label):
                await self.connection.execute(
                    "UPDATE izvorni_zapisi SET status_povezivanja=$2 WHERE id=$1",
                    evidence,
                    status,
                )
                await self.connection.execute(
                    "UPDATE izvori_podataka SET uvoz_dopusten=$2 WHERE id=$1",
                    self.source,
                    allowed,
                )
                await self.connection.execute(
                    "UPDATE objekti SET podrijetlo=$2 WHERE id=$1",
                    location,
                    {
                        key: {"source_record_id": str(pointer)}
                        for key in ("longitude", "latitude")
                    },
                )
                rows = await self.repository.list_locations(LocationQuery(q="Target"))
                self.assertEqual(len(rows), 1)
                self.assertIsNone(rows[0]["longitude"])
                self.assertIsNone(rows[0]["latitude"])
                self.assertNotIn("longitude", rows[0]["field_sources"])
                self.assertEqual(
                    await self.repository.list_locations(
                        LocationQuery(q="Target", bbox=(15, 45, 16, 46))
                    ),
                    [],
                )
                self.assertEqual(
                    await self.repository.list_locations(
                        LocationQuery(q="Target", near=(15.98, 45.81), radius_m=1000)
                    ),
                    [],
                )
