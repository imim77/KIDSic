# Plan: RAG bez rangiranja, uz teme koje bira MCP klijent

Cilj je ukloniti leksičko i vektorsko rangiranje iz `dohvati_kontekst_vrtica`.
Namjeru pitanja određuje model MCP klijenta preko strukturiranog parametra
`topics`. Server deterministički vraća sve prihvaćene dokaze za te teme unutar
odabrane ustanove/objekta. Sve postojeće granice ostaju: opseg, izvori, datumi,
višeznačnost i budžet odgovora.

## 1. Istraživanje

### Trenutni tok (necommitano na grani `codex/rag-context`)

Cijela RAG značajka još nije commitana. To uključuje alat, servise, embedding
indeks i migraciju 0008, pa se uklanjanje ne kosi s objavljenim stanjem.

1. `RagTools.call_tool` (`src/KIDSic/api/rag_tools.py`) validira `RagQuery`
   (`city`, `name`, `question`, `feature_id`) i poziva `RagService.retrieve`.
2. `RagService.retrieve` (`src/KIDSic/services/concrete/rag.py:59`) unutar jedne
   read-only snimke:
   - dohvaća objekte preko `work.locations.list_locations`;
   - vraća `not_found` ili `clarification_required` (više ustanova ili više od
     20 objekata) bez dokaza;
   - iz pitanja izdvaja pojmove (`EvidenceRanker.terms`) i preko
     `work.search.retrieve_context` dohvaća `knowledge_chunk` dokumente.
     Leksički se koristi `OR` pojmova i `limit=30`, a hibridno svi dokumenti s
     `all_documents=True, limit=None`;
   - `RagEvidenceBuilder.collect` gradi dokaze iz strukturiranih zapisa
     (kontakti, povijesni programi i mjesta, aktualni programi, sufinanciranje)
     i iz dokumenata (`topic='document'`).
3. Nakon zatvaranja snimke dokaze rangira `EvidenceRanker.rank` ili
   `HybridRanker.rank`. Zatim se bira najviše 12 dokaza do 24.000 znakova.

### Što leksički dio stvarno radi

`EvidenceRanker` (`rag.py:11-48`) ima dvije uloge:

- **Usmjeravanje na temu** (`accepts`). Tablica prefiksa `_topics` mapira riječi
  pitanja na teme i tvrdo filtrira dokaze. Ako nijedan prefiks ne pogodi, filtar
  ne vrijedi i odlučuje bodovanje.
- **Bodovanje** (`score`). Broji podudaranja preko `term[:4]` prefiksa i dodaje
  +5 za temu. Dokumenti umjesto toga koriste `ts_rank` iz SQL-a
  (`_lexical_score`, `rag_evidence.py:43`).

Slabosti:

- Hrvatska morfologija pokrivena je ručnim prefiksima. Pitanja izvan liste
  („Gdje se nalazi?”, „Radno vrijeme?”) završavaju s `no_evidence`.
- SQL koristi `websearch_to_tsquery('simple', '"upis" OR …')`, dakle točne
  leksme bez stemminga (`asyncpg_kindergarten.py:141,160`). `upis` ne pogađa
  `upisa`, što se ne slaže s prefiksnom logikom u Pythonu.
- `HybridRanker` (OpenAI `text-embedding-3-small`, 384 dimenzije, prag 0,45)
  postoji uglavnom da zakrpa ove propuste. Uvodi ključ, migraciju, naredbu za
  indeksiranje, predmemoriju i prag koji nije kalibriran (vidi RAG.md, odjeljak
  „OpenAI embedding indeks”).

### Zašto rangiranje ovdje ne donosi vrijednost

- Korpus je unaprijed sužen na jednu ustanovu i njene objekte. Strukturirani
  dokazi su nekoliko odlomaka u pet tema, a hibridni način već dohvaća sve
  dokumente u opsegu.
- Alat poziva LLM (ChatGPT, Claude), koji pitanje na hrvatskom razumije bolje
  od tablice prefiksa ili praga sličnosti.
- `RagEvidence.topic` je već `Literal['programs', 'vacancies', 'subsidies',
  'contacts', 'document']` (`src/KIDSic/dto/rag.py:53`), pa enum postoji.

### Sve upotrebe koje promjena dodiruje

Pronađeno pretragom
`grep -rniE "embedding|HybridRanker|EvidenceRanker|RAG_MIN|OPENAI|lexical|retrieval"`.

| Mjesto | Uloga |
| --- | --- |
| `services/concrete/rag.py` | `EvidenceRanker`, poziv `retrieve_context` s `text`, grananje na `_hybrid` |
| `services/concrete/hybrid_ranker.py` | RRF spajanje leksičkog i kosinusnog poretka |
| `services/concrete/embedding_index.py`, `commands/index_embeddings.py`, `pyproject.toml:22` | naredba `kidsic-index-embeddings` |
| `integrations/{interfaces,concrete}/…embedding.py` | OpenAI HTTP klijent |
| `dao/{interfaces,concrete}/…embedding.py`, `db/uow/{base,source,asyncpg,asyncpg_source}.py` | `work.embeddings` repozitorij |
| `dto/embedding.py`, `dto/rag.py` (`_lexical_score`, `RagRetrieval`, `RagContext.retrieval`) | embedding DTO-i i metapodaci dohvata |
| `services/concrete/rag_evidence.py:43-44` | prijenos `lexical_rank` u dokaz |
| `factories/rag.py`, `services/dependency.py:53-70` | spajanje embedding klijenta, `httpx` u `conversation_services` |
| `config/settings.py:25-27,42-45,71-73`, `.env.example:14-18` | `OPENAI_API_KEY`, `EMBEDDING_TIMEOUT`, `RAG_MIN_SIMILARITY` |
| `exceptions.py:38` | `EmbeddingError` |
| `db/alembic/versions/0008_rag_embeddings.{py,sql}` | tablica `rag_embedding` |
| `dao/concrete/asyncpg_kindergarten.py:141` | stupac `lexical_rank` dodan na ovoj grani |
| `api/rag_tools.py` | opis alata spominje hibridni dohvat; sheme polja |
| testovi | `test_hybrid_rag.py`, `test_embedding_database.py`, `test_embedding_http.py`, `test_historical_database.py:175-210`, `test_rag.py`, `fixtures/rag_queries.json`, `test_mcp_server.py:48-90` |
| dokumentacija | `RAG.md`, `MCP.md:151-164`, `TO-DO.md:50`, `README.md` |

**Izvan opsega:** `KindergartenSearchService.recommend`
(`services/concrete/kindergarten_search.py:13-26`) je stariji, commitani kod.
Koristi `retrieve_context(text=…, embedding=…)` nad `knowledge_chunk.embedding`
iz migracije 0001. Ne dira se. Zato `retrieve_context` zadržava parametre
`text` i `embedding`.

## 2. Pristupi

### A. Teme iz klijenta i sve u opsegu, bez rangiranja (odabrano)

- **Što se mijenja:** `RagQuery` dobiva obavezni `topics`. Server filtrira dokaze
  po temi i vraća ih stabilnim redoslijedom. Uklanjaju se `EvidenceRanker`,
  `HybridRanker` i cijeli embedding stog.
- **Rizik:** klijent može odabrati pogrešnu temu ili poslati preširok skup.
  Odgovor tada sadrži više konteksta, ali nikad dokaze izvan odabranog vrtića.
- **Kompromis:** najmanje koda i determinističko ponašanje, uz oslanjanje na
  klijentov LLM. Ugovor alata se mijenja, a za necommitanu značajku to je
  prihvatljivo.

### B. Popraviti leksički dio i zadržati embeddinge kao opciju

- **Što se mijenja:** prefiksni tsquery (`upis:*`), `unaccent` i usklađivanje
  Python i SQL logike.
- **Rizik:** tablica prefiksa ostaje ručno održavana, a hrvatska morfologija
  ostaje djelomično pokrivena. Embedding stog i dalje treba kalibraciju praga.
- **Kompromis:** zadržava slobodno pitanje kao jedini ulaz, uz najveću
  složenost.

### C. Samo embeddingi, bez leksičkog dijela

- **Rizik:** slabo radi na točnim pojmovima (Montessori, telefon, e-mail), a
  prag 0,45 nije kalibriran. I dalje treba usmjeravanje na temu.
- **Kompromis:** ne smanjuje složenost i uvodi vanjsku ovisnost u svaki upit.

### D. Uvijek vratiti sve dokaze, bez `topics`

- **Rizik:** dulje subvencijske politike s tarifama mogu potrošiti budžet od
  24.000 znakova prije kontakata ili programa. Odgovor tada postaje
  `truncated`, iako je pitanje usko.
- **Kompromis:** najjednostavnije, ali bez kontrole veličine. Vrijedi kao
  mjerilo: ako mjerenje (korak 0 niže) pokaže da svi dokazi uvijek stanu,
  `topics` može postati neobavezan.

## 3. Odabrani pristup (A)

### Korak 0: mjerenje (napravljeno 5. 11. 2026.)

Mjereno je na lokalnoj bazi (`docker-compose.yaml`, port 55432, revizija s
0008). Privremena skripta je izvan repozitorija. Za svaku ustanovu
(`list_locations` po gradu, grupirano po `kindergarten_id`) i za svaki objekt
zasebno skripta je pozvala `RagEvidenceBuilder.collect` sa svim dokumentima u
opsegu (`retrieve_context(all_documents=True, limit=None)`). Mjerila je
`len(content)` po temi.

Baza: 545 objekata, 304 ustanove (Zagreb 266, Varaždin 25, Rijeka 13) i 95
`knowledge_chunk` redaka ukupno. Jedna ustanova ima više od 20 objekata, pa
ionako dobiva `clarification_required`.

| Skup | Znakova medijan / p90 / max | Odlomaka medijan / p90 / max | Stane u 12 / 24.000 |
| --- | --- | --- | --- |
| Po objektu (`feature_id`) | 2.123 / 3.391 / 3.620 | 4 / 5 / 6 | 545 / 545 |
| Po ustanovi (svi objekti) | 1.468 / 3.802 / 6.172 | 4 / 15 / 27 | 268 / 304 |

Po temi, na razini ustanove:

| Tema | Max znakova | Max odlomaka | Ne stane |
| --- | --- | --- | --- |
| `subsidies` | 2.492 | 1 | 0 |
| `document` | 4.028 | 14 | 1 (DV Rijeka) |
| `contacts` | 864 | 24 | 23 |
| `vacancies` | 781 | 1 | 0 |
| `programs` | 242 | 1 | 0 |

Zaključci:

- **Budžet znakova nikad nije dosegnut.** Najveći skup ima četvrtinu budžeta
  (6.172 od 24.000 znakova, oko 2.000 tokena).
- **Granica od 12 odlomaka jedino je stvarno ograničenje.** Pogađa 36 ustanova,
  i to samo kad se upit odnosi na sve objekte. Uzrok su kontakti po objektu (do
  24 kratka odlomka) i dokumenti DV Rijeka (14). Ni filtriranje po temama to ne
  rješava, jer i sami `contacts` ne stanu u 23 slučaja.
- **Dokumentima ne treba retrieval.** Najviše ih je 14 po ustanovi, ukupno
  4.028 znakova. `question` stoga nije potreban ni za dokumente.
- **`topics` nije nužan za veličinu odgovora.** Svi dokazi stanu i bez njega.
  Vrijednost `topics` je samo u manje šuma za klijentov model.

Posljedica za plan: `topics` postaje neobavezan i bez njega se vraćaju sve
teme. Granica broja odlomaka uklanja se, a budžet znakova ostaje kao zaštita.
Pristup D je zapravo podskup pristupa A.

**Ponovljeno mjerenje nakon uvoza upisnih dokumenata (5. 11. 2026.).** Ista
metoda, nakon `kidsic-sync-enrolment` (787 novih odlomaka za 61 gradski vrtić
Zagreba). Po ustanovi: 1.468 / 10.947 / 12.423 znakova (medijan / p90 / max) i
4 / 27 / 41 odlomak; svih 304 stane u 24.000 znakova. Tema `document` ima
najviše 8.394 znakova i 15 odlomaka (DV Duga), ispod granice od 30 dokumenata.
Zaključak koraka 0 vrijedi: dohvat nad dokumentima nije potreban.

### Ugovor alata (`src/KIDSic/dto/rag.py`)

- Dodati `Topic = Literal['programs', 'vacancies', 'subsidies', 'contacts',
  'document']` i koristiti ga u `RagEvidence.topic` i `RagQuery.topics`.
- Dodati neobavezni `RagQuery.topics: list[Topic] | None`. `None` znači sve
  teme. Prazan popis se odbija, a duplikati se uklanjaju validatorom.
- Ukloniti `question`, jer ga server više ne koristi. Korak 0 pokazuje da ni
  dokumenti ne trebaju pretragu.
- Ukloniti `RagEvidence._lexical_score`, `RagRetrieval` i `RagContext.retrieval`.

### Servis (`src/KIDSic/services/concrete/rag.py`)

- Obrisati `EvidenceRanker` i parametre `ranker` i `hybrid`.
- Dokumente dohvaćati samo kad `topics` uključuje `'document'` ili je `None`, preko
  `retrieve_context(..., all_documents=True, limit=30)`. `text` se ne šalje.
  Gornja granica od 30 i `truncated` pri 30 ostaju kao sada. Validacija limita
  u `asyncpg_kindergarten.py:131` to već dopušta.
- Filtrirati `evidence` po `topics` i sortirati stabilno: redoslijed tema iz
  enuma, zatim `reference_date` silazno (`None` na kraj), zatim `citation_id`.
- Ukloniti granicu od 12 odlomaka i zadržati budžet od 24.000 znakova bez
  rezanja. Prema koraku 0, granica od 12 odlomaka nepotrebno skraćuje 36
  ustanova, a budžet znakova nijednu. `test_bounded_context_…` u `test_rag.py`
  treba prilagoditi.
  Komentar „Network calls happen after releasing…” više nije potreban, jer
  nakon snimke nema mrežnih poziva.
- Ažurirati docstring modula, jer više nema „lexical retrieval”.

### Ostale izmjene

- `rag_evidence.py`: ukloniti `lexical_rank` granu.
- `asyncpg_kindergarten.py`: vratiti `ts_rank(...) AS lexical_rank`, dodan na
  ovoj grani. `s.license` i `all_documents` ostaju.
- `factories/rag.py`: `create(uow_factory)` bez embedding klijenta.
- `services/dependency.py`: `conversation_services` bez `httpx` klijenta.
  Ukloniti `_embedding_client` i `embedding_index_service`.
- Obrisati embedding datoteke iz tablice gore, `EmbeddingError`, postavke i
  `.env.example` unose te skriptu u `pyproject.toml`.
- Migracija 0008: lokalno prvo pokrenuti
  `uv run alembic -c src/KIDSic/db/alembic/alembic.ini downgrade 0007_historical_records`,
  pa tek onda obrisati datoteke. Inače `alembic` ne nalazi trenutnu reviziju.
- `api/rag_tools.py`: opis polja `topics` mora za svaku temu reći što pokriva.
  Primjerice, „jelovnik, radno vrijeme i upis” idu pod `document`. Opis mora
  reći i kada alat ne pozivati: kad tema ne postoji, odgovor je „podatak nije
  dostupan”. Ukloniti rečenicu o hibridnom dohvatu i ažurirati primjer.

### Testovi

- `test_rag.py`: pitanja zamijeniti s `topics`. Test za pitanja bez teme
  (`test_missing_topic_…`) postaje test da `topics=['document']` bez dokumenata
  vraća `no_evidence` i ne vraća programe ni mjesta. Dodati test da se dokumenti
  ne dohvaćaju kad `'document'` nije među temama. Test budžeta ostaje.
- `fixtures/rag_queries.json`: provjera prepoznavanja teme iz teksta prelazi na
  klijenta, pa fiksture postaju suvišne. Zamijeniti ih parametriziranim testom
  po temi i kombinaciji tema.
- `test_mcp_server.py:60`: `required` postaje `['city', 'name']`.
  Proširiti nevaljane argumente (prazan popis, nepoznata tema).
- `test_historical_database.py:175-210`: hibridni test obrisati. Revokacija i
  zamjena snimke već su pokrivene testom iznad (`:165-173`). Pod
  `KIDSIC_TEST_DATABASE_URL` provjeriti da i dalje prolazi s `topics`.
- Obrisati `test_hybrid_rag.py`, `test_embedding_database.py` i
  `test_embedding_http.py`.

### Dokumentacija

`RAG.md` treba prepisati odjeljke „Poziv i odabir”, „Dohvat i podrijetlo”
(zadnji odlomak) i „OpenAI embedding indeks”. Ažurirati i `MCP.md:151-164`,
`TO-DO.md:50` te `README.md`, gdje se spominje hibridni dohvat.

### Provjera

```sh
uv run python -m unittest discover -s tests -v
KIDSIC_TEST_DATABASE_URL=… uv run python -m unittest discover -s tests -v
grep -rniE "embedding|EvidenceRanker|HybridRanker|RAG_MIN|OPENAI_API" src tests docs *.md
```

Zadnja naredba smije pogoditi samo `kindergarten_search.py`,
`asyncpg_kindergarten.py`, `dao/interfaces/kindergarten.py`, migraciju 0001 i
`test_database.py`. To su stari, commitani `knowledge_chunk` dijelovi.

## 4. Otvorena pitanja

1. **Ostaje li `question`?** Korak 0 to rješava: uklanja se, jer dokumenti ne
   trebaju pretragu. Treba ga vratiti tek uz otvoreno pitanje 2.
2. **Što ako dokumenata po ustanovi bude previše?** Danas ih je najviše 14
   (4.028 znakova). Mjerenje treba ponoviti nakon uvoza upisnih dokumenata.
   Ako tada premaše budžet, retrieval nad
   dokumentima ima smisla. Prvo treba isprobati prefiksni `tsquery` s
   `unaccent`, a embeddinge tek uz evaluaciju na stvarnim upisnim dokumentima.
   To se ne radi sada, jer automatsko preuzimanje dokumenata još ne postoji.
3. **Pretpostavka:** klijentski modeli pouzdano popunjavaju enum iz opisa alata.
   To treba ručno provjeriti u ChatGPT-u i Claudeu na pitanjima iz
   `rag_queries.json` prije brisanja fiksture.
4. **Je li migracija 0008 primijenjena negdje osim lokalno** (staging, dijeljena
   baza)? Ako jest, treba nova migracija koja briše `rag_embedding`, umjesto
   brisanja datoteke 0008.

## Proširenje ruta na Zagreb (6. 11. 2026.)

Istraživanje: `api/commute_tools.py` → `services/concrete/commute.py` →
`services/concrete/day_route.py` → postojeći LocationService i baza. Zagreb je već
u imeniku. Grad, okvir, kalendar, izvor i adresni indeks trenutno su vezani uz
Rijeku u DTO-u, servisu, MCP opisu, frontend parseru i routing skriptama.
ZET potvrđuje Otvorenu dozvolu RH na
https://www.zet.hr/preuzimanja/odredbe/datoteke-u-gtfs-formatu/669.
Arhiva https://www.zet.hr/gtfs-scheduled/scheduled-000-000397.zip ima SHA256
2ddf4051147837545bc1b77af5a82bc8961096da630b11fe7a1079ce3654edf8.
Kalendar ima sve tjedne zastavice ugašene; stvarni dodani datumi u
calendar_dates.txt su 21. 10. – 31. 12. 2026., usprkos feed_end_date=20301231.

Pristupi: jedan zajednički graf oba grada olakšao bi pokretanje, ali bi tražio
ponovnu izgradnju riječkog grafa i proširio indeks adresa bez razdvajanja grada.
Odabrano: zajednički kod s postavkama po gradu i zasebni graf/indeks za Zagreb
(port 18081). Postojeće putanje i port Rijeke ostaju zadani.

Dodati postavke izvora, SHA256, kalendara i okvira po gradu. DTO provjerava
koordinate prema odabranom gradu; servis pretražuje katalog tog grada; MCP bira
ruter i adresni indeks tog grada. Frontend provjerava rezultate prema gradu.
Routing skripte dobivaju --city i pripremaju Zagreb u routing/data/zagreb.
Dokumentirati licencu, atribuciju, datume i naredbe. Provjeriti izolaciju gradova,
kalendare, MCP poziv, frontend prikaz i stvarni lokalni OTP izračun.

Preostale nepoznanice: uspjeh OTP uvoza, trajanje rangiranja cijelog zagrebačkog
kataloga i pokrivenost adresa u lokalnom OSM snapshotu. Provjeriti tijekom
implementacije; ne zamjenjivati nedostupne rute procijenjenim vremenima.


Rezultat provjere: graf Zagreba izgrađen je iz prikvačenog ZET-a i OSM-a.
Lokalni MCP poziv nad stvarnom bazom, Ilica 10 → Radnička cesta 1, 6. 11. 2026.
u 07:00, uspješno rangira 358 objekata u 31,5 sekundi (357 dostupnih ruta).
Primjeri i ograničenja uvoza zabilježeni su u routing/README.md i zasebnom
zagreb-manifest.json. Python: 187 testova, 72 preskočena zbog vanjskih testnih
ovisnosti. Frontend: 101 test, lint, standardni i MCP build prolaze.

## Proširenje na Šibenik — manje radne cjeline (6. 11. 2026.)

### Istraživanje i opseg

Postojeći tok je `api/commute_tools.py` → `CommuteService` → `DayRouteService`
→ LocationService/repozitorij i lokalni OTP. Opći imenik/RAG koriste katalog
`dto/municipality.py`, a normalizator odbacuje gradove izvan tog kataloga.
Uvoz nacionalnog registra stvara sjedišta ustanova, nikad automatski objekte.
Šibenik nije u katalogu; Zagreb proširenje već je u radnom stablu i čuva se.
Stara migracija 0005 je povijesno čišćenje, a ne ograničenje tablice: ne mijenja
se; nakon nje novi grad može ući redovnim uvozom.

Otvoreni izvori:
- MZOM https://data.gov.hr/ckan/dataset/djecji-vrtici — Otvorena dozvola RH,
  sedam polja, šest ustanova za Šibenik/Brodaricu. Hozana je pod zagrebačkim
  sjedištem; podružnica traži zasebno povezivanje na postojeću ustanovu.
- OSM snapshot Hrvatske 2026-11-04T21:21:03Z — ODbL. Samo imenovani objekti
  s adresom i provjerenim odnosom prema ustanovi ulaze u planiranje ruta.
  Neimenovani zapisi i neprovjerene adrese nisu kandidati za preporuku.
- Gradski parking https://www.gradski-parking.hr/stranice/datoteke-u-gtfs-formatu/105.html
  izričito navodi Otvorenu dozvolu za static i realtime. Preuzeti ZIP ima SHA256
  6fd33879adc8a57e66fab75dbdcebc9136b383be0e7a7274e0accb4561530128,
  227 stajališta, 32 zapisa linija, 346 vožnji i 5.319 stop_times zapisa.
  Kalendar 2026-09-07–2027-06-07; bez shapes.txt. Koristi se raspored, bez RT.

### Pristupi i odluka

Uvoz svih web-stranica dao bi više objekata/programa, ali otvorene licence
za taj sadržaj nisu potvrđene. Odabrano: MZOM ustanove i odvojena pregledana
OSM snimka objekata. To daje manju, ali dokazivu pokrivenost. Kod ne smije
pretvoriti sjedišta u objekte ni obećavati potpunost fizičkih lokacija.
Zaseban šibenski OTP/indeks na portu 18082 čuva postojeće grafove.

### Radne cjeline

1. Imenik: dodati grad/alias i potvrđenu Brodaricu unutar šibenske županije;
   proširiti opće MCP/RAG opise i testove. Nacionalni uvoz ostaje isti izvor.
2. Objekti: dodati ponovljiv pregledani OSM uvoz s provjerom nepromijenjenih
   nacionalnih roditelja, stabilnim identitetima, atomskim aktiviranjem i
   provjerom source.import_allowed. Dopune iz web-stranica ne ulaze u podatke.
3. Promet: dodati RoutingCity, SHA256 i datume, gradom odvojene putanje/env,
   normalizaciju Šibenik/22000, OSM okvir i Docker profil. Izgraditi stvarni graf.
4. Integracija: proširiti DTO i frontend provjere grada/okvira, MCP metapodatke,
   testirati gradsko filtriranje, idempotentnost uvoza, nedostupne izvore,
   povrat stare snimke, pogrešne koordinate/datum i stvarni MCP izračun.

### Otvorena pitanja

Pregled svih OSM oznaka još treba potvrditi konačan broj prihvatljivih objekata.
Adresna pokrivenost i kvalitetni prometni spojevi provjeravaju se na stvarnom
grafu. Bez shapes.txt OTP može konstruirati prometnu geometriju; treba provjeriti
što prikazuje karta. Pravila konkretnog datathona nisu dostavljena; potvrđujemo
licence izvora, ne prihvatljivost prema nepoznatim pravilima natjecanja.


### Rezultat Šibenik

Sve četiri cjeline su implementirane. Nacionalni uvoz dodao je šest ustanova;
imenik za Šibenik vraća sedam zapisa (tri objekta i četiri sjedišta), uključujući
podružnicu Hozane sa zagrebačkim roditeljem. Pregledana OSM snimka prihvaća tri
objekta i isključuje četiri nedovoljno potvrđena kandidata. Ponovljeni uvoz,
promjena roditelja, zabrana izvora i očuvanje aktivne snimke provjereni su u
izoliranoj PostgreSQL bazi migriranoj od nule.

Šibenski OTP radi na 18082; graf ima 227 stajališta/32 obrasca, adresni indeks
4.564 zapisa. Manifest bilježi hashove, licence, opseg i upozorenja. Zbog
nedostatka shapes.txt autobusna geometrija povezuje stajališta; to je navedeno
u dokumentaciji i detaljima puta. Nepotpuna pokrivenost vrtića navedena je i u
MCP odgovoru i UI-ju. Mrežni MCP na 8002 provjeren je sa stvarnom bazom i
OTP-om: Svilajska 20 → Ulica Velimira Škorpika 10, 9. 11. 2026. u 07:00,
tri uspoređena i tri dostupna objekta, autobus/hodanje, oko 0,3 sekunde.
Stvarni odgovor prolazi frontend parser, dekodiranje geometrija i render.

Python: 193 testa, 3 preskočena jer CKAN/Postman simulator nije pokrenut;
svih 190 ostalih, uključujući DB testove, prolazi. Frontend: 102 testa,
lint i oba builda prolaze. Posebna privremena provjera stvarnog MCP payload-a
također je prošla i nije ostavljena kao ovisnost redovitih testova.

Preostala ograničenja su pokrivenost fizičkih objekata, kvaliteta izvornog
GTFS-a i nedostajući otvoreni podaci o programima/radnom vremenu/mjestima.
Pravila datathona nisu pretpostavljena; navedene su stvarne licence izvora.
