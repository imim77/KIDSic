# Plan: pojednostavniti shemu baze uz dokaze trenutačnog stanja

**Status:** cjeline 1–5 provedene su i zabilježene u odjeljku 7. Odjeljci
1–6 čuvaju istraživanje i izvorni prijedlog; donesene odluke imaju prednost
pred ondje navedenim otvorenim pitanjima. Aktualna shema je na reviziji
`0019_croatian_tables`. Korak 2c proveden je u odjeljku 11; cjelina 6
ostaje odgođena.

Model čuva dokaze trenutačnog stanja, ali ne arhivu njihovih promjena.
Stabilan `source_record_id` nakon uvoza može sadržavati drukčiji izvorni tekst.
Dump prije migracije omogućuje obnovu tog trenutka; ne čuva svaku kasniju
verziju izvora niti sam omogućuje reprodukciju svih prijašnjih odgovora.

Cilj je ukloniti dijelove sheme koje nitko ne puni ni ne čita, čuvati samo
trenutačno stanje svakog izvora umjesto svih snimki i prestati kopirati isti
upisni tekst za svaki gradski vrtić. Pravila podrijetla ostaju ista: aktivni izvor, prihvaćen
zapis, isti vlasnik/objekt, datumi i licenca. Javni MCP/HTTP ugovori se ne
mijenjaju, osim u cjelini 4, koja je izričito odluka o funkcionalnosti.

Prethodni plan (RAG bez rangiranja, rute za Zagreb i Šibenik) je proveden i
ostaje u povijesti gita, revizija `de0b1ed`. Ova verzija uključuje recenziju
prve verzije od 6. 11. 2026.

## 1. Istraživanje

### Kako je shema nastala

Osam migracija u `src/KIDSic/db/alembic/versions/`. Svaka ima `.py` koji
izvršava pripadni `.sql`, s naredbama odvojenima retkom `-- statement`.

- `0001_simple_rag` kreira `data_source`, `kindergarten`, `location`,
  `source_record`, `program`, `availability`, `enrolment`, `knowledge_chunk`.
  Prva naredba je `CREATE EXTENSION IF NOT EXISTS vector` (redak 1).
- `0002` dodaje `municipality`, `seat_*` stupce na `kindergarten`, te
  `enrolment.municipality_id` i `enrolment_scope_check`.
- `0003` dodaje koordinate sjedišta i view `kindergarten_seat_geography`.
- `0005` briše podatke izvan tadašnjih gradova (Zagreb, Varaždin, Rijeka).
  To je zapis stanja podrške u to vrijeme, a ne greška.
- `0006` dodaje `municipality_subsidy_policy`, `0007` `historical_record`,
  `0008` `enrolment.round` i `accepting`.

### Snimke (batch)

Svaki uvoz piše nove `source_record` retke s novim `batch_id`, pa prebacuje
`data_source.active_batch_id` na njega (`asyncpg_source.py:211`,
`asyncpg_enrolment.py:99`, `asyncpg_historical.py:62`, `Batch` u
`scripts/reviewed_snapshot.py`). Stari retci se nikad ne brišu. Svi upiti za dokaze traže
`s.active_batch_id=r.batch_id`.

Postoji jedna iznimka: `asyncpg_location.py:14-22` (`approved_record`) čita i
neaktivne zapise. Razlog je što provenance polja (`kindergarten.provenance`,
`location.provenance`, JSON s `source_record_id`) može pokazivati na stariju
snimku. API to izlaže zastavicom `active_snapshot` (`dto/location.py:85`,
`asyncpg_location.py:174`).

Stare snimke danas služe dvjema stvarima:

- **Zadržane vrijednosti.** Ako novi red nema vrijednost, uvoz zadržava staru.
  To vrijedi za `COALESCE` u `asyncpg_source.py:193` i za `provider_kind`
  (`:137`, provenance se ažurira samo kad red nije `unknown`). Provenance
  tada pokazuje na stari zapis. Lokalno postoji jedan takav slučaj:
  `provider_kind` jednog vrtića iz stare snimke imenika `national`, jer novi
  red daje `unknown`.
- **Ponovno prepoznavanje.** `asyncpg_source.py:64` za svaki `source_key`
  traži zadnju prihvaćenu vezu kroz sve snimke. Tako zapis koji nestane i
  vrati se zadržava vlasnika. Lokalno nijedan ključ iz stare snimke ne
  nedostaje u aktivnoj, pa se to još nije dogodilo.

Zapise i `active_batch_id` pišu četiri mjesta: `asyncpg_source.py:211`,
`asyncpg_enrolment.py:99`, `asyncpg_historical.py:62` i
`Batch.source`/`Batch.record` u `scripts/reviewed_snapshot.py`. Pet
skripti pregledane geografije (Varaždin, Rijeka, Šibenik, sjedišta obrta)
piše isključivo preko `Batch`.

**`source_key` nije jedinstven unutar izvora.** `source_record.source_key`
je uvijek popunjen, ali ključ `varazdin-primary-venue` pojavljuje se 10 puta u
`varazdin-other-osm-18a5f04e778a1af0` i 5 puta u
`varazdin-other-venue-a16ccf2ded9adcd5`, unutar iste snimke i za različite
ustanove. Ključ je `item['location_key']` u
`scripts/import_other_varazdin.py`, koji je isti za svaku ustanovu
čija je lokacija njezino glavno mjesto.

### Izmjereno stanje (lokalna baza, 6. 11. 2026.)

| | Ukupno | Aktivna snimka | Stare snimke |
| --- | --- | --- | --- |
| `source_record` | 1.652 | 913 | 739 |
| `knowledge_chunk` | 2.477 (107 tekstova) | 870 (106 tekstova) | 1.607 |
| `zagreb-enrolment-notice-2026-2027` | 1.131 | 377 | 754 (2 stare snimke) |
| `zagreb-enrolment-page` | 1.098 | 366 | 732 |
| `zagreb-preschool-notice-2026-2027` | 132 | 44 | 88 |
| `enrolment` | 244 | 122 (61 vrtić × 2 poziva) | 122 |
| `historical_record` | 423 | 423 | 0 |

Provenance polja pokazuju na 752 aktivna zapisa i **1 neaktivan**.

Ostalo:

| Tablica / stupac | Stanje |
| --- | --- |
| `availability` | 0 redaka |
| `program` | 0 redaka |
| `knowledge_chunk.embedding`, `embedding_model`, `program_id` | 0 popunjenih |
| `enrolment.steps`, `documents` | 122 neprazna, ostatak ranijeg uvoza |
| `location.postal_code` | 0 od 447 |
| `kindergarten.seat_postal_code` | 243 od 310 |
| `location.county` / `kindergarten.seat_county` | 50 / 229 |
| `location.municipality_id` | 447 od 447 |
| `location.kind='unknown'` | 72 |

Upiti za ponovno mjerenje:

```sql
SELECT (s.active_batch_id=r.batch_id) active, count(*), count(DISTINCT c.content)
FROM knowledge_chunk c JOIN source_record r ON r.id=c.source_record_id
JOIN data_source s ON s.id=r.source_id GROUP BY 1;

WITH refs AS (
  SELECT (f.value->>'source_record_id')::uuid id FROM kindergarten k, jsonb_each(k.provenance) f
  WHERE f.value ? 'source_record_id'
  UNION SELECT (f.value->>'source_record_id')::uuid FROM location l, jsonb_each(l.provenance) f
  WHERE f.value ? 'source_record_id')
SELECT (s.active_batch_id=r.batch_id) active, count(DISTINCT r.id)
FROM refs JOIN source_record r ON r.id=refs.id JOIN data_source s ON s.id=r.source_id GROUP BY 1;
```

### Tko što piše i čita

**`availability`.** Nijedan SQL u `src/` ni `scripts/` je ne spominje.
Spominju je samo testovi ograničenja (`tests/test_database.py:179`,
`tests/test_source_database.py:92,123`). `historical_record.vacancies` čuva
povijesna mjesta. Ona ostaju povijesna i nisu zamjena za buduću aktualnu
raspoloživost.

**Embeddingi.** `KindergartenSearchService.recommend`
(`services/concrete/kindergarten_search.py:13`) i `retrieve_context`
(`dao/concrete/asyncpg_kindergarten.py:127`) primaju vektor. Ni CLI
(`commands/search.py`) ni RAG (`services/concrete/rag.py:41`) ga ne predaju.
Koriste ga samo `tests/test_database.py:59-135`.

**`enrolment.steps` i `documents`.** Nijedan `INSERT` ih ne puni
(`asyncpg_enrolment.py:92`) i nijedan upit ih ne čita. Koraci i dokumenti
čitaju se iz citiranog izvora (`dto/location.py:104`).

**`program` se aktivno koristi.** Iz njega rade dobni filtar i filtar programa
alata `prikazi_vrtice` (`api/location_tools.py:61-138`), `valid_program` u
`asyncpg_kindergarten.py:61` i `asyncpg_location.py:24`, te RAG dokazi o
aktualnim programima. Postoje i integracijski testovi. Tablica je prazna jer
nijedan uvoz ne piše `INSERT INTO program`. Uz nju idu
`data_source.stale_after_days` i `knowledge_chunk.program_id`.

**Leksička grana trenutačno nije dostupna.** `kidsic-search` poziva
`retrieve_context(text=…)` samo za vrtiće s potvrđenom dobi
(`kindergarten_search.py:20-28`). Uz prazan `program` takvih nema. RAG je
zaobilazi s `all_documents=True`.

**`location.postal_code` nije propust.** `national.py:78` izričito tretira
adresu iz imenika kao pravno sjedište (`scope='institution'`), pa poštanski
broj ide u `seat_postal_code`. Isto vrijedi za `childminder.py:30`. Izvori
objekata poštanski broj ne daju.

**`location.kind='unknown'` je legitimno stanje.** Izvor nije naveo je li
objekt matični ili područni, a uvoz ne nagađa.

### Upisni dokumenti: zašto se kopiraju

`AsyncpgEnrolmentDocumentRepository.import_document`
(`dao/concrete/asyncpg_enrolment.py:18`) ovako radi:

1. Pri uvozu određuje vlasnike: aktivne ustanove traženih `provider_kinds`
   u gradu, prema sjedištu ili aktivnom objektu.
2. Za svakog vlasnika piše vlastiti `source_record`, iste odlomke i iste
   upisne krugove.

Kopiranje rješava dva stvarna problema:

1. **Vrsta pružatelja.** `municipality_id` ne zna za `provider_kinds`, pa bi
   gradski red zahvatio i privatne vrtiće. Zato `asyncpg_location.py:115`
   čita samo krugove ustanove.
2. **Zamrznut obuhvat.** Ustanova uvezena nakon pregleda ne dobiva dokument.

Odlomci imenovanih ustanova (`excerpt.institutions`) i iznimke
(`call.not_accepting` → `accepting=false`) već su po ustanovi i nisu kopije.
`EnrolmentRoundSelector` (`services/concrete/enrolment_round.py:17-24`)
pravilo nadjačavanja primjenjuje po pedagoškoj godini. Ako ustanova odbija
upis za godinu, njeni opći krugovi te godine se ne nude.

Čitatelji upisa:
- `retrieve_context` (`asyncpg_kindergarten.py:141-170`) spaja odlomak i zapis
  preko `r.kindergarten_id=c.kindergarten_id`, a opseg čita iz
  `r.raw_data->>'scope'`.
- `RagEvidenceBuilder` (`rag_evidence.py:41`) od toga gradi
  `scope='municipality'` ili `'institution'`.
- `asyncpg_location.py:115-128` gradi `rounds` za karticu vrtića.

### Sjedište ustanove

Sjedište zauzima 11 stupaca na `kindergarten`. Piše ga `asyncpg_source.py:158-165`,
a geografiju `scripts/import_childminder_geography.py`. Čitaju ga
`asyncpg_location.py`, `asyncpg_kindergarten.py`, `asyncpg_enrolment.py`,
`asyncpg_historical.py` i `services/concrete/location.py`.

View `kindergarten_seat_geography` (0003) radi dvije stvari:
- povezuje sjedište s dokazom preko teksta iz JSON-a
  (`k.provenance->'seat_geography'->>'source_record_id'`);
- odbacuje koordinate kad se `k.seat_address` ne podudara s
  `k.seat_attributes->>'address'`. Koordinate tada pripadaju staroj adresi.

## 2. Pristupi

### Stare snimke

- **A. Zadržati sve.** Stare snimke čine 45 % zapisa i 65 % odlomaka. Nijedan
  dokazni upit ih ne vraća.
- **B. Brisati neaktivne zapise nakon uvoza.** Uvoz i dalje stvara punu
  snimku, a zatim briše staru, osim zapisa na koje pokazuje provenance.
  Model ostaje složen: snimke, iznimke za referencirane zapise i
  ponovno prepoznavanje kroz povijest.
- **C. Samo trenutačno stanje izvora (odabrano).** Uvoz ažurira zapis na
  mjestu prema `(source_id, source_key)`, uz stabilan `id`. Dodaje nove
  zapise, a uklanja nestale zajedno s izvedenim retcima. Starih snimki nema,
  pa ih nije potrebno čistiti. Veze (`provenance`, `knowledge_chunk`,
  `enrolment`, `program`) ostaju ispravne jer `id` ostaje isti. Odluka o
  povezivanju, uključujući ručne, ostaje na istom retku.
  Cijena: nema povijesti promjena, a zapis koji nestane pa se vrati ponovno
  prolazi povezivanje. To se lokalno još nije dogodilo. Za povijest izvora
  postoje samo eksplicitno spremljeni `pg_dump` i seedovi; oni nisu potpuna
  povijest promjena izvora.

### Obuhvat upisnih dokumenata

Zajedničko svim varijantama: tekst postoji jednom po izvornom zapisu. Isti
tekst iz različitih izvora, datuma ili obuhvata **ne** spaja se.

- **A. Status quo.** Jedna kopija po ustanovi.
- **B. Pravilo za opće pozive, poveznice za imenovane (preporuka).** Opći
  dokument ima pravilo „grad + vrste pružatelja”. Imenovani dokumenti i
  iznimke imaju poveznice na ustanove. Ustanova uvezena kasnije dobiva gradsku
  obavijest. To odgovara stvarnosti, jer gradska obavijest vrijedi za sve
  gradske vrtiće. Svrha 2 gubi se samo za opće pozive.
- **C. Zamrznut popis.** Tablica s parovima (zapis, ustanova). Čuva obje
  svrhe, ali za 61 vrtić i dalje drži 61 redak po zapisu. Uklanja kopije
  teksta, ali ne i kopije obuhvata.

Između B i C odlučuje vlasnik; vidi otvoreno pitanje 1. Zaštita „ustanova
aktivna na datum objave” nije izvediva: re-import zamjenjuje snimku imenika,
pa se datum prvog pojavljivanja ustanove ne čuva.

### Sjedište

- **A. `location` s `kind='seat'`.** Svaki upit za kartu, rute,
  `clarification_required` i provjeru aktivnosti pretpostavlja da je lokacija
  fizički objekt. Odbijeno.
- **B. Tablica `kindergarten_seat` 1:1 (odabrano).** Parser već razlikuje
  sjedište od objekta (`national.py:78`), pa se semantika ne mijenja.
- **C. Status quo.**

## 3. Odabrani pristup

Šest cjelina, svaka s vlastitom migracijom i commitom. Svaka mora biti zelena
prije sljedeće. Prije svake migracije napraviti `pg_dump` lokalne baze.

### Cjelina 1: usko čišćenje (`0009_remove_unused`)

Shema:
- `DROP TABLE availability`.
- `knowledge_chunk`: ukloniti `embedding`, `embedding_model`, njihove CHECK-ove.
- `enrolment`: ukloniti `steps` i `documents`.

**Proširenje `vector` i pgvector u slici ostaju.** `0001` izvršava
`CREATE EXTENSION vector`, pa slika bez pgvectora ne može instalirati bazu
od nule. Naknadni `DROP EXTENSION` to ne rješava. Uklanjanje bi tražilo
izmjenu 0001 (prepisivanje povijesti) ili uvjetnu naredbu u njoj. Ušteda je
samo jedno proširenje u slici, pa se to ne radi.

`knowledge_chunk.program_id`, `program` i `stale_after_days` ostaju do
cjeline 4.

Kod:
- `retrieve_context` (`dao/interfaces/kindergarten.py`,
  `dao/concrete/asyncpg_kindergarten.py:127`) gubi `embedding`,
  `embedding_model`, granu `vector`, kolonu `distance` i `import math` ako
  ostane nekorišten.
- `KindergartenSearchService.recommend` i njegovo sučelje gube `embedding`
  i `embedding_model`.
- README: ukloniti rečenicu o predanom embeddingu.

Testovi:
- ukloniti embedding testove (`tests/test_database.py:59-135`), a ostale
  provjere opsega iz njih prenijeti na leksički poziv;
- iz `test_availability_and_enrolment_scope_constraints` (`:179`) ukloniti
  `availability`, a dio za `enrolment` zadržati;
- u `tests/test_source_database.py:92,123` ukloniti `availability`.

Downgrade vraća stupce i tablicu prazne.

### Cjelina 2: samo trenutačno stanje izvora (`0010_current_source_state`)

Uvodi se u dva koraka. Prvi korak ne mijenja nijedan upit za čitanje.

**Korak 2a: preduvjeti.**
- `import_other_varazdin.py` piše jedinstven ključ po ustanovi, npr.
  `f"{item['kindergarten_id']}:{item['location_key']}"`, a migracija na isti
  način ispravlja postojeće retke. Ispraviti samo jedno od to dvoje vratilo
  bi ponovljeni ključ pri sljedećem uvozu.
- `provider_kind` vrtića čiji dokaz postoji samo u staroj snimci treba
  pregledani izvor, kao u migraciji 0004. Nasljeđivanje se ne smije
  zamijeniti s `unknown`, jer bi vrtić ispao iz filtra `provider_kind`,
  pravila sufinanciranja i općeg upisnog obuhvata (cjelina 3, varijanta B).
  Upit iz odjeljka 1 pokazuje sve takve slučajeve.

**Korak 2b: zajednička operacija zamjene stanja.**

`SourceStateWriter` (ime je prijedlog) prima izvor, `fetched_at` i retke s
`source_key`. Unutar transakcije i uz advisory lock
`pg_advisory_xact_lock(194733, 1)` radi sljedeće:

1. Provjerava novi skup prije ikakve izmjene: nije prazan i nema ponovljenih
   ključeva. Pri grešci ništa se ne mijenja.
2. Ažurira postojeće zapise prema `(source_id, source_key)` uz isti `id`, a
   dodaje nove.
3. Briše nestale zapise i njihove izvedene retke redom ovisnosti, jer FK
   nemaju `ON DELETE CASCADE`: `knowledge_chunk`, `enrolment`, `program`,
   zatim `source_record`.
4. Postavlja `batch_id` svih zapisa izvora na novi batch i prebacuje
   `active_batch_id`. Zato svi postojeći filtri
   `s.active_batch_id=r.batch_id` rade bez promjene.

Sva četiri pisca iz odjeljka 1 koriste tu operaciju. Za skripte je dovoljno
promijeniti `Batch` u `reviewed_snapshot.py`. Ne smije ostati drugi put
pisanja, jer bi se model raspao.

Shema (`0010`):
- obrisati sve zapise neaktivnih snimki i njihove izvedene retke, osim
  zapisa na koje pokazuje provenance;
- dodati `UNIQUE(source_id, source_key)` na `source_record`. Ograničenje
  pada ako korak 2a nije dovršen, i to je namjerno.

`historical_record` se ne mijenja; vidi cjelinu 6. Njegovi „mjesta na dan
1. 1. 2025.” namjerno su povijesni sadržaj, a ne stara snimka.

**Vrijednosti koje izvor više ne daje.**
- Kontakti, koordinate, četvrt i slično postaju nepoznati, ali samo ako
  provenance polja pokazuje na isti izvor. Polje koje dokazuje drugi izvor
  (npr. `rijeka-reviewed-geography`) uvoz ne dira. To zamjenjuje
  `COALESCE` u `asyncpg_source.py:193`.
- Polja koja određuju klasifikaciju (`provider_kind`, `name`) ne postaju
  tiho nepoznata. Uvoz ili zadržava vrijednost uz dokaz drugog aktivnog
  izvora, ili pada s popisom vrtića kojima treba pregled.
- Provenance više nikad ne pokazuje na nepostojeći zapis. Zastavica
  `active_snapshot` (`asyncpg_location.py:174`) tada je uvijek `true`.
  Uklanja se u koraku 2c.

**Korak 2c (kasnije, mehanički):** ukloniti `batch_id`, `active_batch_id`,
filtre `s.active_batch_id=r.batch_id`, `approved_record`/`active_snapshot`
u `asyncpg_location.py` i potragu kroz snimke u `asyncpg_source.py:64`.
Ta potraga postaje obično čitanje postojećeg retka po ključu.

Očekivani rezultat na lokalnoj bazi: oko 738 manje `source_record`, 1.607
manje `knowledge_chunk` i 122 manje `enrolment` redaka. Svaki sljedeći uvoz
zadržava isti broj redaka umjesto da ga udvostruči.

Testovi (`tests/test_source_database.py`, `test_enrolment_database.py`,
`test_location_database.py`):
- ponovni uvoz istog skupa ne mijenja `id` ni broj redaka;
- nestali zapis se briše zajedno s odlomcima i upisnim krugovima;
- ponovljeni `source_key` ili prazan skup ruše uvoz bez ikakve izmjene;
- kontakt koji izvor više ne daje postaje nepoznat, a polje drugog izvora ostaje;
- `provider_kind` ne pada tiho u `unknown`;
- ručna odluka o povezivanju preživi ponovni uvoz;
- opoziv izvora (`import_allowed=false`) i dalje skriva sve.

### Cjelina 3: upisni dokumenti bez kopija (`0011_document_scope`)

Ovdje je opisana varijanta B. Ako vlasnik odabere C, `document_scope` sadrži
samo retke s `kindergarten_id`.

Shema:
```sql
-- DocumentScope određuje kome dokument vrijedi: pravilom ili imenovanjem.
CREATE TABLE document_scope (
 source_record_id uuid NOT NULL REFERENCES source_record(id),
 municipality_id uuid REFERENCES municipality(id),
 provider_kinds text[],
 kindergarten_id uuid REFERENCES kindergarten(id),
 CHECK ((municipality_id IS NOT NULL AND provider_kinds IS NOT NULL AND kindergarten_id IS NULL)
     OR (municipality_id IS NULL AND provider_kinds IS NULL AND kindergarten_id IS NOT NULL))
);

-- EnrolmentRefusal čuva objavljeno neprihvaćanje s izvorom i krugom.
CREATE TABLE enrolment_refusal (
 enrolment_id uuid NOT NULL REFERENCES enrolment(id),
 kindergarten_id uuid NOT NULL REFERENCES kindergarten(id),
 source_record_id uuid NOT NULL REFERENCES source_record(id),
 PRIMARY KEY (enrolment_id, kindergarten_id)
);
```

- `source_record.kindergarten_id` i `knowledge_chunk.kindergarten_id` smiju
  biti NULL za zapis s pravilom. CHECK ili okidač osigurava da takav zapis
  ima redak u `document_scope`.
- `enrolment` dobiva jedan red po pozivu. `accepting` se uklanja, jer ga
  zamjenjuje `enrolment_refusal`. Pedagoška godina i izvor dolaze preko
  `enrolment_id`, a nadjačavanje ostaje kao u `EnrolmentRoundSelector`:
  odbijanje za godinu skriva opće krugove te godine za tu ustanovu.
- `enrolment.municipality_id` i `enrolment_scope_check` uklanjaju se, jer
  obuhvat sada određuje `document_scope`.
- Migracija ne pretvara postojeće redove. Briše upisne zapise
  (`data_source.metadata->>'kind'='enrolment_document'`) i ovisne retke, a
  upute traže ponovni `kidsic-sync-enrolment`. Snimke su u
  `src/KIDSic/db/seeds/`.

Kod:
- `import_document`: za opći dokument piše jedan `source_record`, jedan
  `document_scope` s pravilom i odlomke jednom. Imenovani odlomci ostaju po
  ustanovi, s retkom u `document_scope`. `not_accepting` postaje
  `enrolment_refusal`. Provjera da imenovane ustanove postoje i da je pravilo
  pogodilo barem jednu aktivnu ustanovu ostaje kao danas.
- `retrieve_context` i `asyncpg_location.py` (`rounds`) dobivaju istu
  provjeru primjenjivosti:
  - zapis pripada vrtiću (`r.kindergarten_id`), ili
  - `document_scope` imenuje vrtić, ili
  - pravilo pogađa vrtić: `provider_kind = ANY(provider_kinds)` i grad
    sjedišta ili aktivnog objekta jednak `municipality_id`. Isti uvjet danas
    ima `import_document`.

  Provjeru treba napisati jednom, npr. kao SQL funkciju ili view
  `document_applicability`, a ne kopirati je u dva upita.
- Komentar u `asyncpg_location.py:115` ažurirati, jer pravilo sada nosi vrstu
  pružatelja.

Očekivani rezultat za aktivnu snimku: oko 106 odlomaka umjesto 870 i 2 retka
`enrolment` umjesto 122.

Testovi (`test_enrolment_database.py`, `test_rag.py`, `test_location_database.py`):
- privatni vrtić u Zagrebu ne dobiva gradski krug ni obavijest;
- imenovani dokument ne prelazi na drugu ustanovu;
- iznimka skriva opće krugove samo svoje godine;
- opoziv izvora skriva sve;
- dokaz ima isti `scope`, `applies_to` i datume kao prije;
- za varijantu B: ustanova dodana kasnije dobiva gradsku obavijest.

### Cjelina 4: odluka o `program`, dobnom filtru i CLI-ju

Ovo nije čišćenje nego odluka o funkcionalnosti javnih alata; vidi otvoreno
pitanje 2. Ishodi su:
- **Uvoz programa.** Napisati uvoz koji puni `program`. Tada leksička grana
  CLI-ja i `knowledge_chunk.program_id` postaju dostupni.
- **Uklanjanje.** Ukloniti `program`, `stale_after_days`,
  `knowledge_chunk.program_id`, `age_months`/`program` iz `prikazi_vrtice`,
  `find_options(age…)`, RAG temu aktualnih programa i, ako ostane bez svrhe,
  `kidsic-search` s leksičkom granom. Povijesni programi iz
  `historical_record` ostaju.

### Cjelina 5: sjedište i županija (`0013_kindergarten_seat`)

- `kindergarten_seat(kindergarten_id PK FK, address, postal_code, settlement,
  settlement_key, municipality_id, longitude, latitude, attributes,
  geography_source_record_id FK)`. Podaci se prenose iz `seat_*` stupaca,
  a zatim se ti stupci brišu.
- `geography_source_record_id` zamjenjuje `provenance->'seat_geography'`.
  **Provjera da geokodirana adresa (`attributes->>'address'`) odgovara
  trenutačnoj `address` mora ostati**, u viewu ili u upitima. Bez nje bi se
  koordinate stare adrese prikazivale uz novu. Sam pravi FK ne uklanja tu
  krhkost.
- `seat_county` i `location.county` se uklanjaju; županija se čita iz
  `municipality`. Migracija prvo provjerava usklađenost i pada s popisom
  razlika umjesto da ih prešuti. Izvorna vrijednost ostaje u `raw_data`.
- `location.postal_code` ostaje.
- Svi čitatelji iz popisa „Sjedište ustanove” prelaze na
  `LEFT JOIN kindergarten_seat`.

### Cjelina 6: `historical_record` (možda nikad)

Dijeli sedam stupaca sa `source_record`, ali ima drugačiju jedinstvenost
(`UNIQUE(source_id,batch_id,source_key)`) i zaseban životni ciklus. Razmotriti
tek nakon cjelina 1–5, i to samo ako postoji konkretan problem.

## 4. Izvan opsega

- `location.kind='unknown'` ostaje; to je istinito stanje izvora.
- `municipality.supported` ima smisla tek ako baza postane jedini autoritet
  za podržane gradove. Danas je to kod.

## 5. Otvorena pitanja

1. **Obuhvat općih dokumenata: pravilo (B) ili zamrznut popis (C)?** Treba
   odgovor prije cjeline 3. Preporuka je B.
2. **Puni li ikad netko `program`?** Treba odgovor prije cjeline 4. Bez uvoza
   dobni filtar uvijek vraća „dob nepoznata”, a dio javnog ugovora alata ne
   radi ništa.
3. **Je li gubitak povijesti prihvatljiv?** Cjelina 2 pretpostavlja da
   povijest promjena izvora i prepoznavanje zapisa koji nestane pa se vrati
   nisu zahtjevi. Ako jesu, vrijedi varijanta B iz odjeljka 2.
4. **Kako pregledati `provider_kind` bez izvora** (korak 2a)? Moguće je
   dodati pregledani izvor kao u 0004 ili ostaviti `unknown` uz svjesno
   prihvaćanje posljedica.
5. **Starije baze.** Cjelina 3 briše upisne zapise i traži ponovni uvoz.
   Pretpostavka je da su sve baze lokalne i obnovljive iz `seeds/`.

## 6. Provjera

Za svaku cjelinu:

```sh
uv run alembic -c src/KIDSic/db/alembic/alembic.ini upgrade head
KIDSIC_TEST_DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/kidsic_test \
  uv run python -m unittest discover -s tests -v
```

Zatim:
- provjeriti `downgrade -1` i ponovni `upgrade head` na kopiji baze;
- provjeriti instalaciju od nule na zasebnoj praznoj testnoj bazi ili novom
  spremniku s vlastitim volumenom (`upgrade head`), bez brisanja radnog
  volumena. Time se potvrđuje da 0001 i dalje radi.

Za cjeline 2 i 3: usporediti izlaz `dohvati_kontekst_vrtica` za DV Duga
(`topics=["document"]`) i karticu jednog zagrebačkog gradskog vrtića prije i
poslije, uz ponovljena mjerenja iz odjeljka 1. Dokazi, datumi, `scope` i
`applies_to` moraju biti jednaki.

## 7. Provedba

Odluke vlasnika od 6. 11. 2026.: cjelina 3 koristi pravilo B; cjelina 4
uklanja aktualne programe, dobne/programske filtre i neiskorištenu CLI pretragu.
Korak 2c i objedinjavanje historical_record ostaju odgođeni kako plan navodi.

- Cjelina 1: migracija 0009, leksički dohvat bez embedding ugovora.
  Provjeren upgrade, downgrade i ponovni upgrade na zasebnoj bazi;
  192 testa prolaze (3 vanjske simulacije preskočene). Sigurnosna kopija
  lokalne baze: Docker spremnik database, /tmp/kidsic_before_0009.dump.

- Cjelina 2: stabilni source_record ID-jevi, jedinstveni ključevi i zajednički
  SourceStateWriter za pisanje/brisanje/aktivaciju. historical_record zadržava
  zasebnu povijest (cjelina 6); dijeli aktivaciju i zaključavanje.
  Izmjereno nakon 0010: 913 source_record, 870 knowledge_chunk, 122 enrolment,
  423 historical_record. RAG za DV Duga i kartice identični su prije/poslije.
  U bazi je sporni provider_kind već unknown; dokaz je povezan s aktivnim
  zapisom iste ustanove i ključa bez promjene klasifikacije. Poznate vrijednosti
  bez aktivnog dokaza migracija odbija. Upgrade/downgrade/upgrade prolaze;
  195 testova prolazi (3 vanjske simulacije preskočene). Backup: /tmp/kidsic_before_0010.dump.

- Cjelina 3: document_scope, enrolment_refusal i zajednički view
  document_applicability. Nakon migracije seedovi su ponovno uvezeni dvaput;
  ukupno 771 source_record, 106 knowledge_chunk, 2 enrolment, 423 historical_record.
  DV Duga: cijeli RAG odgovor i kartice identični prije/poslije. Provjeren
  downgrade/upgrade; 198 testova prolazi (3 simulacije preskočene).
  Backup: /tmp/kidsic_before_0011.dump.

- Cjelina 4 (odluka vlasnika: uklanjanje): migracija 0012_remove_programs,
  uklonjeni aktualni programi, dobni/programski filtri, pokazatelji prikladnosti,
  kidsic-search i leksička grana. Povijesni programi ostaju pod temom programs.
  Sjedište je zbog zasebne migracije ove cjeline pomaknuto na 0013.
  Provjeren downgrade/upgrade, 181 poslužiteljski test i 97 frontend testova,
  TypeScript/Vite za web i MCP te ESLint.

- Cjelina 5: migracija 0013_kindergarten_seat, svi čitatelji/pisci i pregledani
  geografski uvozi koriste novu tablicu. Provjera županije odbija razlike;
  FK geografski dokaz ne zamjenjuje provjeru adrese i vlasnika. Svih 310
  sjedišta ima identična prenesena polja i geografske reference.
  Provjeren upgrade/downgrade/upgrade i na kopiji popunjene baze.
  Svih pet skripti pregledane geografije prolazi dry-run nad lokalnim podacima.
  Backup prije migracije: /tmp/kidsic_before_0013.dump u Docker spremniku database.

Završna provjera: novi odvojeni Docker spremnik iz iste slike instalira sve
revizije od 0001 do 0013 na praznoj bazi (bez diranja postojećeg volumena).
184 poslužiteljska testa prolaze, uz 3 preskočene vanjske simulacije;
97 frontend testova, oba produkcijska builda i ESLint prolaze.
RAG za DV Duga, uključujući citate, datume, scope i applies_to, identičan je
početnom odgovoru; kartice se razlikuju samo po uklonjenim programskim poljima.
Ponovni uvoz upisnih seedova nakon 0013 zadržava završne brojeve:
771 source_record, 106 knowledge_chunk, 2 enrolment i 423 historical_record.
Početni dump kopiran je i na host: /private/tmp/kidsic_before_reconstruction_20261106.dump.
Korak 2c i cjelina 6 ostaju odgođeni; nema preostalih odluka za cjeline 1–5.

## 8. Dorada nakon pregleda

### Istraživanje i opseg

`CkanClient.download_records` preuzima cijeli JSON ili CSV; nema DataStore
paginacije ni očekivanog ukupnog broja redaka. `SourceService._snapshots`
normalizira sve izvore prije transakcije. `AsyncpgSourceRepository` zatim
zamjenjuje stanje pod zajedničkim advisory lockom. Valjana, ali nepotpuna
datoteka danas može ukloniti ranije ključeve kroz `SourceStateWriter.finish`.
Pregledani lokalni dokumenti i geografske skripte imaju zasebne, namjerno
zadane obuhvate; ova zaštita odnosi se na CKAN uvoz imenika.

`database/README.md`, `ERA.md` i izvoznik modela još opisuju staru reviziju
0006. Migracija 0014 već uklanja nečitani trigram indeks/proširenje,
generirani `location.position`, `knowledge_chunk.content_sha256` i prazna
sjedišta. Te postojeće migracije ne treba ponovno provoditi nad radnom bazom.

### Pristupi i odluka

- Prag dopuštenog pada broja redaka: jednostavan, ali propušta manje gubitke
  i zamjenu starih ključeva novima uz jednak broj redaka.
- Odabrano: odbiti svaki gubitak prethodnih ključeva prije promjene podataka,
  osim uz izričit `allow_removals=True` odnosno `--allow-removals`. Poruka
  navodi izvor, broj i uzorak nestalih ključeva za pregled. Provjera se radi
  pod istim zaključavanjem kao zamjena; neuspjeh vraća cijelu transakciju.

Ova provjera štiti postojeće zapise; ne dokazuje potpunost prvog uvoza ni
potpunost sadržaja unutar retka. Bez izvornog manifesta takav dokaz nemamo.
Promjena izvornog ključa također traži pregled. Prazni i duplicirani skupovi
ostaju zabranjeni i uz dopušteno uklanjanje.

### Provedba i provjera

Provesti opciju kroz naredbu, servis i DAO sučelje. Usporediti ključeve prije
registracije/projekcija u `asyncpg_source.py`. Testirati odbijanje nepotpunog
skupa, zamjenu uz isti broj redaka, rollback svih odabranih izvora i izričito
dopušteno uklanjanje s čišćenjem izvedenih podataka. Ažurirati dokumentaciju
i generirati rječnik, manifest i dijagram iz zasebne baze na reviziji 0014.
Nema novih migracija ni promjena podataka radne baze.

### Rezultat dorade

Provedeno: CKAN uvoz zadano odbija nestale ključeve, a `--allow-removals`
odnosno servisni/DAO argument dopušta pregledano uklanjanje. Poruka daje
izvor, broj i do deset ključeva. Provjera štiti i zamjenu ključeva uz jednak
broj redaka. Testovi potvrđuju rollback metapodataka, kanonskih polja,
izvedenih redaka i prethodno obrađenih izvora.

Integracijski test uklanjanja objekta otkrio je postojeću grešku u
`SourceStateWriter._forget_fields`: obvezni `location.kind` postavljao se na
NULL. Gubitkom njegova dokaza sada prelazi u `unknown`.

Nova baza `kidsic_test_import_guard_20261106` instalirana je od 0001 do 0014.
Cijeli poslužiteljski skup: 188 testova, OK, 3 vanjske simulacije preskočene.
Izvoznik generira 12 tablica i 2 pogleda na reviziji 0014; obnovljeni su
manifest, rječnik i Graphviz dijagram. Ažurirani su oba README-a i ERA.md.
`database/` i `scripts/export_database_model.py` i dalje su lokalno ignorirani
prema postojećoj politici repozitorija. Radna baza nije mijenjana.

## 9. Preostala poboljšanja (pregled na reviziji 0014)

Brojevi migracija u ovom odjeljku izvorni su prijedlog. Revizija 0015 sada
je `valid_knowledge_chunk`, a kaskadno brisanje provedeno je u 0016 (odjeljak
10). Preostale migracije treba prenumerirati prije provedbe.

Na reviziji 0014 nema nekorištenih tablica ni stupaca: svih 12 tablica se
čita (`spatial_ref_sys` pripada PostGIS-u). Ovaj odjeljak bilježi ono što bi
se moglo izvesti jednostavnije. Reference su imena funkcija jer se kod
paralelno mijenja; brojeve redaka treba ponovno provjeriti prije provedbe.

### Istraživanje

**Brisanje izvedenih redaka je ručno.** Svih 25 stranih ključeva u shemi ima
pravilo `NO ACTION`. `SourceStateWriter.clear_derived` i `finish`
(`dao/concrete/source_state.py`) zato brišu redom `enrolment_refusal`,
`knowledge_chunk`, `enrolment`, `document_scope` i tek onda `source_record`.
Nova tablica izvedena iz zapisa mora se ručno dodati u taj popis, inače
brisanje pada na stranom ključu. Odgođeni okidači iz 0011
(`check_document_scope`) okidaju se i na `DELETE` iz `document_scope`.

**Snimke više ništa ne razlikuju.** Nijedan od 771 `source_record` ni 423
`historical_record` retka nije izvan aktivne snimke (upit iz odjeljka 1).
Filtar `s.active_batch_id=r.batch_id` i dalje stoji na 11 mjesta u 9
datoteka (`asyncpg_location.py` ×2, `source_state.py` ×2, te po jedno u
`asyncpg_enrolment.py`, `asyncpg_historical.py`, `asyncpg_kindergarten.py`,
`asyncpg_source.py`, `scripts/reviewed_snapshot.py`,
`scripts/import_rijeka_geography.py`, `scripts/import_sibenik.py`).
`asyncpg_historical.py` i dalje stvara novu snimku pri svakom uvozu
(`batch = uuid4()`, zatim `INSERT INTO historical_record`), pa je to jedini
pisac kojem `batch_id` još nešto znači.

**Podaci aplikacije stoje u `raw_data` i `metadata`.** Upisni uvoz u
`source_record.raw_data` 12 zapisa upisuje `kind`, `scope`,
`reference_date`, `date_kind`, `valid_until`, `document_url` i
`snapshot_key`. To nisu izvorni podaci nego odluke aplikacije, a SQL ih čita
kao stupce: `AsyncpgKindergartenRepository.retrieve_context` (`kind`, `scope`,
`reference_date`, `valid_until`) i `rounds` u `AsyncpgLocationRepository`
(`document_url`, `reference_date`, `date_kind`). `scope` postoji dvaput, u
`raw_data` i u tablici `document_scope`, koja je od 0011 izvor istine.
`data_source.metadata->>'kind'='enrolment_document'` služi kao vrsta izvora u
viewu `document_applicability` i u upitu vlasnika u `asyncpg_enrolment.py`.
`historical_record` već ima `reference_date` i `date_kind` kao prave stupce.

**Provenance je JSON bez stranog ključa.** `kindergarten.provenance` i
`location.provenance` čuvaju `polje → {source_record_id}` kao tekst.
`SourceStateWriter._forget_fields` ima 49 redaka koji ručno oponašaju
`ON DELETE`: traže tekstualne reference na obrisane zapise, brišu ključeve iz
JSON-a i vraćaju vrijednosti polja. U tom je kodu odjeljak 8 našao grešku
(`location.kind` je postajao NULL). `provenance` se spominje na 36 mjesta u
kodu, a čitatelji spajaju preko `r.id::text`.

### Pristupi

**Brisanje izvedenih redaka**
- A. Zadržati ručni redoslijed. Radi, ali svaka nova izvedena tablica traži
  izmjenu `clear_derived`.
- B. `ON DELETE CASCADE` na stranim ključevima izvedenih redaka (odabrano).
  Brisanje zapisa postaje jedan `DELETE FROM source_record`. Rizik je da
  cascade obriše više nego što treba, pa se smije staviti samo na retke koji
  bez zapisa nemaju smisla, nikad na `kindergarten` ni `location`.

**Snimke**
- A. Zadržati `batch_id` dok ga koristi `historical_record`.
- B. Prebaciti povijesni uvoz na zamjenu na mjestu, pa ukloniti snimke
  posvuda (odabrano; to je korak 2c iz cjeline 2).

**Podaci aplikacije u `raw_data`**
- A. Stupci na `source_record` (`date_kind`, `valid_until`, uz postojeći
  `observed_on`) i `data_source.kind`. Bez spajanja, ali s NULL vrijednostima
  za oko 760 zapisa imenika.
- B. Zasebna tablica `document_record(source_record_id PK, reference_date,
  date_kind, valid_until)`. `source_record` ostaje općenit, ali svaki
  čitatelj dobiva jedan JOIN više.

Oba pristupa uklanjaju čitanje `raw_data` kao stupaca. Odluka je otvoreno
pitanje 2; za `scope` u oba slučaja vrijedi `document_scope`.

**Provenance**
- A. Zadržati JSON (odabrano za sada).
- B. Tablica `field_evidence(entity, entity_id, field, source_record_id FK)`.
  Uklanja viseće reference i spajanje preko teksta, ali ne uklanja brisanje
  vrijednosti polja kad dokaz nestane; to i dalje radi kod. Dotiče sve
  čitatelje i pisce provenancea, pa je opravdano tek ako taj kod nastavi rasti.

### Odabrani pristup

Redoslijed je od najmanjeg zahvata prema najvećem. Svaka cjelina ima svoju
migraciju i commit, a prije svake treba napraviti `pg_dump` radne baze.

**Cjelina 7: `ON DELETE CASCADE` za izvedene retke (`0015`).** Promijeniti
strane ključeve `knowledge_chunk.source_record_id`, `enrolment.source_record_id`,
`enrolment_refusal.source_record_id`, `enrolment_refusal.enrolment_id` i
`document_scope.source_record_id` u `ON DELETE CASCADE`. Zatim iz
`clear_derived` i `finish` ukloniti ručna brisanja tih tablica.
`kindergarten_seat.geography_source_record_id` treba posebnu odluku jer uz
referencu treba obrisati i koordinate (otvoreno pitanje 1). Provjeriti da
odgođeni okidači iz 0011 i dalje propuštaju cascade brisanje cijelog
dokumenta. Testovi: brisanje nestalog zapisa uklanja sve izvedene retke;
brisanje ustanove i dalje pada dok postoje njezini zapisi.

**Korak 2c: ukloniti snimke (`0016`).** Preduvjet: `AsyncpgHistoricalRepository`
zamjenjuje retke na mjestu prema `(source_id, source_key)`, kao
`SourceStateWriter`, i briše nestale. Zatim ukloniti
`data_source.active_batch_id`, `source_record.batch_id`,
`historical_record.batch_id`, indekse `ix_record_batch` i
`ix_historical_record_batch` te svih 11 filtara. Provjera aktivnog izvora
svodi se na `s.import_allowed`, a `SourceStateWriter.activate` samo bilježi
`fetched_at` i `observed_on`. Na kopiji baze usporediti `list_locations` za
sva četiri grada i RAG kontekst za svaku ustanovu prije i poslije.

**Cjelina 8: podaci aplikacije izvan `raw_data` (`0017`).** Prema odluci iz
otvorenog pitanja 2 dodati stupce ili tablicu, prenijeti vrijednosti iz
`raw_data` 12 upisnih zapisa i `data_source.metadata->>'kind'` u pravi
stupac s CHECK ograničenjem. `scope` čitati iz `document_scope`. Upisni uvoz
(`asyncpg_enrolment.py`) piše nove stupce, a `raw_data` čuva samo izvorni
sadržaj. Provjera: RAG odgovor za DV Duga (`topics=["document"]`) i upisni
krugovi zagrebačkog gradskog vrtića identični su prije i poslije.

**Cjelina 9: `field_evidence` (opcionalno).** Pokrenuti samo ako se
`_forget_fields` ili čitatelji provenancea nastave širiti; vidi pristup B gore.

### Izvan opsega

- Jedan `DOMAIN` za vrste pružatelja. Popis se ponavlja u tri CHECK
  ograničenja, ali nije isti: `municipality_subsidy_policy` (0006) namjerno
  isključuje `other` i `unknown`, pa domena ne bi zamijenila sva tri.
- `enrolment_refusal.source_record_id` je u oba retka isti kao izvor upisnog
  kruga, ali `rounds` u `asyncpg_location.py` preko njega provjerava aktivnost
  i primjenjivost odbijanja. Ostaje.
- Indeksi na stranim ključevima poput `knowledge_chunk.location_id`. Najveća
  tablica ima 771 redak, pa indeks ne bi ništa ubrzao.

### Otvorena pitanja

1. **Koordinate sjedišta kad nestane geografski dokaz.** `ON DELETE SET NULL`
   briše samo referencu; `_forget_fields` danas briše i koordinate. View
   `kindergarten_seat_geography` ih bez reference ionako ne prikazuje. Smiju li
   koordinate ostati u tablici, ili se brisanje zadržava u kodu?
2. **Stupci ili tablica za podatke upisnih dokumenata** (pristup A ili B)?
   `document_url` ne treba ni u jednom: u svih 12 zapisa jednak je
   `data_source.url` (provjereno 6. 11. 2026.), pa ga čitatelj uzima iz izvora.
3. **Ostaje li cjelina 6 (`historical_record` uz `source_record`) i dalje
   odgođena** nakon što korak 2c ujednači način zamjene?

## 10. Provedba kaskadnog brisanja

Migracija `0016_cascade_derived` dodaje `ON DELETE CASCADE` na pet veza:
`knowledge_chunk.source_record_id`, `enrolment.source_record_id`,
`document_scope.source_record_id`, `enrolment_refusal.source_record_id` i
`enrolment_refusal.enrolment_id`. Ne mijenja stupce ni podatke.

`SourceStateWriter.finish` nakon čišćenja provenancea briše samo nestale
izvorne zapise; baza briše njihove izvedene retke. `clear_derived` ostaje za
ponovni uvoz jer on zadržava izvorni zapis i njegov ID. Brisanje odbijanja
preko obrisanog upisnog kruga sada obavlja baza. Geografski dokaz sjedišta
ostaje `NO ACTION`, uz postojeće čišćenje reference, koordinata i atributa
u `_forget_fields`. Veze prema ustanovama i objektima nisu promijenjene.

Provjera: 192 poslužiteljska testa, OK, uz 3 preskočene vanjske simulacije.
Novi testovi pokrivaju izravno kaskadno brisanje dokumenta i upisnog kruga,
rollback, zaštitu ustanove i uklanjanje nestalih skupina pri ponovnom uvozu.
Instalacija od nule te upgrade/downgrade/upgrade kopije popunjene baze prolaze;
brojevi i kontrolni sažeci svih podatkovnih tablica ostaju identični.

Lokalna radna baza nadograđena je na 0016, uključujući prethodno dodani
pogled `valid_knowledge_chunk` iz 0015. Kontrolni sažeci podataka i nakon
primjene identični su početnima. Sigurnosne kopije na hostu:
`/private/tmp/kidsic_before_cascade_20261106.dump` (0014) i
`/private/tmp/kidsic_before_0016_cascade_20261106.dump` (0015).

## 11. Uklanjanje snimki: plan provedbe

Istraživanje: `SourceStateWriter` već ažurira `source_record` po jedinstvenom
paru `(source_id, source_key)`. Povijesni DAO još radi INSERT novih snimki,
uz UNIQUE koji uključuje batch. Dva pogleda iz 0013 i pogled iz 0015 ovise
o batch stupcima. `approved_record` u lokacijama služi starijem provenanceu;
DTO, frontend tip i ugovor lokacija još izlažu `active_snapshot`.

Pristupi: zadržati batch samo za povijest znači ostaviti dva životna ciklusa.
Odabrano je ukloniti ga posvuda i povijesne retke ažurirati prema izvoru i
ključu. Povijesni DAO zadržava postojeće ponovno povezivanje prema aktualnom
imeniku, transakciju, zaključavanje i odbijanje uvoza bez prihvaćenih redaka.

Migracija 0017 uklanja stare povijesne snimke, uvodi UNIQUE(source_id,
source_key) na historical_record te uklanja tri batch stupca i indekse.
Neaktivne source_record retke odbija s porukom za pregled, jer njihove JSON
reference nije sigurno tiho brisati. Rekreira sva tri ovisna pogleda.
Downgrade vraća jednu tehničku snimku po izvoru, bez obnove obrisane povijesti.

Pisci zadržavaju stabilne ID-jeve, brišu nestale ključeve i bilježe vremena
uvoza. Uklanjaju se batch filtri, CLI rezultat batch_id, zastavica
active_snapshot i njezin poseban DTO/tip. Testovi zamjenjuju neaktivne snimke
odbijenim zapisima/opozvanim izvorima; dodaju provjere stabilnih povijesnih
ID-jeva, brisanja nestalih redaka i rollbacka. Nepoznanica je postoje li stare
povijesne snimke u drugim bazama; migracija obrađuje taj slučaj izričito.

Provjera: cijeli poslužiteljski skup na praznoj bazi; frontend testovi i
TypeScript build; upgrade/downgrade/upgrade na kopiji popunjene baze.
Usporediti kartice za sva četiri grada i RAG svake ustanove prije/poslije,
uz izuzimanje namjerno uklonjene zastavice active_snapshot. Prije primjene na
lokalnu radnu bazu napraviti pg_dump. Ostale promjene sheme nisu u opsegu.

### Rezultat uklanjanja snimki

Provedeno u 0017: uklonjena su sva tri batch stupca, oba batch indeksa i
filtri iz čitatelja/pisaca, uključujući sva tri ovisna pogleda. Povijesni uvoz
čuva ID-jeve, ažurira sadržaj i uklanja nestale ključeve uz postojeća pravila
povezivanja. DTO, frontend tip i dokumentacija više nemaju active_snapshot;
CKAN rezultat nema batch_id. Ulazne pregledane datoteke i transakcijske
read-only snimke ostaju zasebni koncepti.

Provjereno: 193 poslužiteljska testa, OK (3 vanjske simulacije preskočene),
97 frontend testova i produkcijski TypeScript/Vite build. Svih pet pregledanih
geografskih skripti prolazi dry-run na kopiji popunjene baze. Posebna provjera
potvrđuje odbijanje neaktivnog source_record uz rollback, uklanjanje starih
historical_record verzija i jedinstvenost novih ključeva. Prazna instalacija
te upgrade/downgrade/upgrade popunjene kopije prolaze.

Lokalna radna baza nadograđena je na 0017. Kartice sva četiri grada i dohvat
RAG dokaza za svih 310 ustanova jednaki su prije/poslije, uz izuzimanje
namjerno uklonjene zastavice active_snapshot. Brojevi i kontrolni sažeci svih
tablica, bez uklonjenih batch stupaca, ostaju identični: 771 source_record,
423 historical_record, 106 knowledge_chunk i 2 enrolment. Sigurnosna kopija:
`/private/tmp/kidsic_before_0017_20261106.dump`. Objedinjavanje historical_record
sa source_record i tipizirani podaci upisnih dokumenata nisu dio ovog zahvata.

## 12. Tipizirani podaci dokumenata: plan

Istraživanje: upisni DAO upisuje aplikacijske datume, obuhvat, URL i oznaku
snimke u raw_data. `valid_knowledge_chunk` iz 0017 čita JSON datume i obuhvat;
upisni krugovi u lokacijskom DAO-u čitaju JSON datum i URL. Vrsta izvora čita
se iz metadata u upisnom DAO-u i document_applicability. Lokalno postoje tri
upisna izvora i 12 zapisa; URL-ovi odgovaraju data_source.url, a observed_on
odgovara objavljenoj vrsti datuma. Drugi izvori nemaju metadata.kind.

Pristupi: stupci na source_record dodali bi neprimjenjive vrijednosti svim
ostalim zapisima; odabrana tablica document_record odvaja dokumente i dopušta
obvezne datume. Migracija 0018 dodaje data_source.kind ('general' ili
'enrolment_document') i document_record(source_record_id PK FK ON DELETE
CASCADE, reference_date NOT NULL, date_kind NOT NULL, valid_until). Ograničenja
provjeravaju published/observed i valid_until >= reference_date.

Migracija prenosi datume i vrstu izvora, rekreira dva ovisna pogleda te uklanja
premještene JSON ključeve samo s upisnih zapisa. URL dolazi iz data_source,
obuhvat iz document_scope, snapshot_key ostaje u metadata izvora. Migracija
odbija neusuglašen URL, oznaku snimke, datum ili obuhvat umjesto gubitka
različite vrijednosti. raw_data čuva preostali izvorni sadržaj; trenutačni
upisni zapisi nemaju dodatan izvorni JSON, a tekst je u knowledge_chunk.

DAO piše dokumentne datume UPSERT-om uz isti source_record ID. Zamjena sadržaja
ne briše document_record; nestali izvorni zapis briše ga kaskadno. SQL više ne
čita premještene JSON ključeve. Pogled ne nudi upisne dokaze bez dokumentnih
datuma. Downgrade rekonstruira stari JSON ugovor iz tablice i metapodataka.

Provjeriti granice datuma, nepoznatu vrstu, kaskadno brisanje, reimport i
rollback. Pokrenuti cijeli poslužiteljski skup na praznoj bazi te
upgrade/downgrade/upgrade popunjene kopije. Usporediti kartice svih gradova i
RAG dokaze svih ustanova prije/poslije. Prije primjene spremiti pg_dump.
Nema preostalih otvorenih odluka; 'general' je zadana vrsta ostalih izvora,
ne tvrdnja da su svi izvori imenici.

### Rezultat tipiziranih podataka dokumenata

Migracija 0018 provedena je na lokalnoj radnoj bazi: 12 document_record redaka,
3 izvora vrste enrolment_document i 29 general izvora. Premješteni ključevi
više nisu u upisnom raw_data ni metadata.kind. Očuvani su ostali podaci izvora,
izvorni JSON, odlomci, obuhvati i podaci svih drugih tablica.

195 poslužiteljskih testova prolazi (3 vanjske simulacije preskočene).
Prazna instalacija te upgrade/downgrade/upgrade popunjene kopije prolaze.
Posebna provjera potvrđuje rollback za sedam neispravnih/proturječnih ulaza,
očuvanje dodatnog izvornog JSON polja te rekonstrukciju datuma i metapodataka
pri downgradeu. Dvostruki probni uvoz pregledanih seedova čuva svih 12 ID-jeva
i datume, 106 odlomaka i 2 upisna kruga; probna transakcija je poništena.

Kartice sva četiri grada, RAG dokazi svih 310 ustanova i datumi svih 12
dokumenata identični su prije/poslije na kopiji i na lokalnoj radnoj bazi.
Kontrolni sažeci ostalih podataka također se podudaraju nakon normalizacije
namjerno premještenih polja. Sigurnosna kopija:
`/private/tmp/kidsic_before_0018_20261106.dump`.

## 13. Hrvatski nazivi tablica: plan

Zahtjev: preimenovati svih 13 aplikacijskih tablica na hrvatski, u množini i
snake_case bez dijakritika. Stupci, pogledi, Python ugovori, indeksi i nazivi
ograničenja ostaju isti. Sistemske tablice ostaju alembic_version i spatial_ref_sys.

Istraživanje: API i servisi koriste DAO ugovore; stvarni nazivi tablica nalaze
se u konkretnim DAO klasama, pet pregledanih geografskih skripti i pomoćnoj
skripti, SQL seedu sufinanciranja i integracijskim testovima. Dinamički SQL
koristi i popise/usporedbe imena u SourceStateWriter i AsyncpgSourceRepository.
Tri pogleda i strani ključevi prate preimenovane PostgreSQL objekte, ali funkcija
check_document_scope iz 0011 sadrži tekstualne SQL reference i TG_TABLE_NAME;
nju nova migracija mora zamijeniti. Testovi starih migracija izravno izvršavaju
njihov SQL, pa njihove testne kopije SQL-a prevode reference na aktualne nazive
tablica, uz očuvanje SQL vrijednosti i stupaca. Stare migracije ne mijenjaju se.

Pristupi: dodatni pogledi sa starim imenima zadržali bi dvostruko imenovanje i
komplicirali upise. Odabrano je ALTER TABLE RENAME i prilagodba svih aktivnih
SQL mjesta. Migracija 0019 čuva podatke i identitete, mijenja funkciju okidača,
a downgrade vraća nazive i staru funkciju.

Dogovorena imena: data_source → izvori_podataka; source_record → izvorni_zapisi;
kindergarten → vrtici; kindergarten_seat → sjedista_vrtica; location → objekti;
municipality → jedinice_lokalne_samouprave; municipality_subsidy_policy →
pravila_sufinanciranja; enrolment → upisni_krugovi; enrolment_refusal →
neprihvacanja_upisa; document_scope → obuhvati_dokumenata; document_record →
zapisi_dokumenata; knowledge_chunk → odlomci_znanja; historical_record →
povijesni_zapisi.

Provjera: instalacija od nule i cijeli poslužiteljski skup, povrat/nadogradnja
popunjene kopije, usporedba svih redaka po kontrolnim sažecima te kartica i
dokaza za sva četiri grada. Provjeriti pet geografskih uvoza i ponovni uvoz
upisnih seedova. Prije lokalne primjene napraviti pg_dump. Otvorenih pitanja
nema; nazivi su potvrđeni prethodnim odgovorom korisnika.

### Rezultat hrvatskih naziva tablica

Migracija 0019 provedena je na lokalnoj radnoj bazi. Svih 13 aplikacijskih
tablica ima dogovorene hrvatske nazive u množini. Sistemske tablice, stupci,
pogledi, nazivi indeksa/ograničenja i javni API nisu promijenjeni. Okidač
check_document_scope koristi nove reference i TG_TABLE_NAME. Aktivni DAO-i,
pet geografskih skripti, SQL seed sufinanciranja, integracijski testovi,
dokumentacija i inventar lokalnog izvoznika modela koriste nove nazive.
Stare migracije ostaju nepromijenjene.

Provjereno: 196 poslužiteljskih testova, OK (3 vanjske simulacije preskočene),
instalacija od nule te upgrade/downgrade/upgrade popunjene kopije. Svih pet
geografskih skripti prolazi dry-run; dvostruki probni uvoz upisnih dokumenata
čuva svih 12 ID-jeva i datume, 106 odlomaka i 2 upisna kruga. Kartice sva četiri
grada, dokazi svih 310 ustanova te točni kontrolni sažeci svih podatkovnih
tablica ostaju identični na kopiji i na radnoj bazi. Radna baza i dalje ima
310 vrtića, 447 objekata i 771 izvorni zapis.

Sigurnosna kopija prije preimenovanja:
`/private/tmp/kidsic_before_0019_20261106.dump`. Prikaz u PyCharmu treba
osvježiti nad shemom public kako bi se učitali novi nazivi.
