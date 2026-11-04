# Gradsko sufinanciranje

[Snimka od 4. studenoga 2026.](2026-11-04_municipal_subsidies.sql) sadrži devet
skupova pravila sa službenih gradskih stranica i službenih glasila. Svaki zapis
sadrži izvore i mjesta u dokumentima. Ne dodaje se API, kalkulator ni prikaz.

Nakon `alembic upgrade head` i uvoza gradova Zagreb, Varaždin i Rijeka:

```sh
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f src/KIDSic/db/seeds/2026-11-04_municipal_subsidies.sql
```

SQL zapis radi u jednoj transakciji. Ponovljeno izvršavanje ažurira istu snimku
i čuva identitete. Nedostajući grad prekida cijeli upis. Ne mijenja objekte,
kontakte, koordinate ni postojeće izvore imenika. Buduće promjene zahtijevaju
novi ključ snimke i zatvaranje prethodnog razdoblja; ne prepisivati povijest.

Tablica `municipality_subsidy_policy` povezuje grad s tipovima pružatelja.
Za budući prikaz kod fizičkog objekta povezati `location.municipality_id` s
`municipality_id` politike i `kindergarten.provider_kind` s `provider_kinds`.
Kod prikaza samo sjedišta koristi se `kindergarten.seat_municipality_id`.
To daje moguće pravilo; ugovor ustanove i pravo pojedine obitelji moraju se
provjeriti zasebno. `unknown` i `other` ne nasljeđuju subvencije javnih vrtića.

Format `rules.schema_version=1` je opisni:

- `*_cents`: cijeli eurocenti po djetetu mjesečno, osim gdje je navedena dnevna osnovica.
- `city_subsidy_cents`, `parent_fee_*` i `economic_price_*` imaju različito značenje.
- `rates`, `eligibility` i `reliefs`: tarife, uvjeti i olakšice; nisu programski izrazi.
- `pending_change`: prijedlog koji se ne smije koristiti kao važeća tarifa.
- `NULL` iznos znači nepoznato, a ne besplatno; status `partial` traži dodatnu potvrdu.
- `valid_until` je uključiv. `NULL` granica znači da nije potvrđena; ne znači trajno pravo.
- `verified_on` označava dan provjere. Prije aktualnog prikaza ponovno provjeriti izvor.

Varaždin: gradski roditeljski udjeli 90/50/25 € i privatne/vjerske subvencije
360/400/425 €, s pravilima za istodobno upisanu djecu i posebne okolnosti.
**Iznos za dadilje nije potvrđen**: odluka iz 9/24 upućuje na zaseban zaključak;
ne pretpostavljamo da automatski vrijedi cjenik privatnih vrtića.

Zagreb: privatni/vjerski vrtići i dadilje 352,54–412,26 €, ovisno o prihodima.
Dodatnih 180 € već je uključeno. Gradski vrtići imaju odvojene roditeljske tarife
za cjelodnevni i poludnevni program te obiteljske olakšice. Državna sredstva
nisu pribrojena gradskoj subvenciji.

Rijeka: drugi osnivači 335 € jaslice / 275 € vrtić, od rujna 2026. do kolovoza
2027.; gradske roditeljske tarife 48/54/70 € za cjelodnevni program. Pragovi
prihoda izraženi su propisanim udjelom prosječne plaće RH, bez nagađanja
aktualne eurske protuvrijednosti. Dadilje 260 €; 310 € ostaje prijedlog u
savjetovanju do 6. studenoga 2026. Godišnji gradski limit djece za dadilje nije
potvrđen broj i ne predstavlja broj djece u jednoj obitelji.
