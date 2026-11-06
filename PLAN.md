# Plan: pojednostavniti shemu baze bez gubitka dokaza

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
SELECT (s.active_batch_id=r.batch_id) active, count(*), count(DISTINCT c.content_sha256)
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
  dovoljni su `pg_dump` i snimke u `seeds/`.

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

### Cjelina 5: sjedište i županija (`0012_kindergarten_seat`)

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
- provjeriti instalaciju od nule (`docker compose down -v`, `up`,
  `upgrade head`). Time se potvrđuje da 0001 i dalje radi.

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
