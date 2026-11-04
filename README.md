# KIDSic

MCP app za pronalazak dječjih vrtića povezivanjem više otvorenih skupova. Implementirani su PostgreSQL model, CKAN registracija izvora i uvoz triju JSON skupova i CSV popisa varaždinskih obrta dadilja, SQL pretraga prema gradu i dobi te RAG dohvat s izvorima. MCP alat `prikazi_vrtice` povezuje obavezan grad s Mapbox kartom i vodoravnim karticama naziva i adresa. Embedding pružatelj još nije implementiran.

Aplikacija podržava samo **Zagreb, Varaždin i Rijeku**. Uvoz preskače zapise
iz drugih gradova prije upisa u bazu; pripadnost gradu određuje se prema
potvrđenoj općini, pa zagrebačka naselja poput Sesveta ostaju uključena.
HTTP API odbija nepodržani grad statusom 422, a MCP alat vraća popis podržanih
gradova. Razgovorna pretraga koristi isti obuhvat.

## Struktura

Organizacija prati [FOIHireloom](https://github.com/imim77/FOIHireloom), pregledan na reviziji `8ba897db799e993aa43c7d488879efb3870218f2`:

```text
src/KIDSic/
  api/                      # HTTP/MCP prezentacijski adapteri
    apps/map_resource.py    # HTML resurs i metapodaci MCP aplikacije
    location_tools.py       # grupa MCP alata za lokacije
    mcp_server.py           # vlasnik MCP transporta i životnog vijeka
  mcp/server.py             # kompatibilni ulaz u api.mcp_server
  commands/                 # izvršne naredbe, bez SQL-a
  config/                   # postavke okruženja
  dao/interfaces/           # ugovori repozitorija
  dao/concrete/             # asyncpg SQL implementacije
  db/
    alembic/                # konfiguracija i verzionirane migracije
    database.py             # asyncpg pool i JSON kodeci
    Dockerfile              # PostgreSQL slika s PostGIS-om i pgvectorom
    models/                 # rezervirano; nema ORM-a u trenutačnoj izvedbi
    uow/                    # transakcije i životni vijek konekcije
  dto/                      # podatkovni ugovori i normalizacija teksta
  factories/                # sastavljanje servisa iz ovisnosti
  integrations/interfaces/  # CKAN ugovor
  integrations/concrete/    # async httpx CKAN klijent i JSON/CSV dohvat
  services/interfaces/      # ugovori poslovnih operacija
  services/concrete/        # poslovna orkestracija, planner i parser upita
    parsers/                # zamjenjivi parseri nacionalnog, Zagreb i CSV izvora
  services/dependency.py    # životni vijek infrastrukture
  main.py                   # ulazna točka
frontend/src/
  shared/                   # zajednički stilovi i resursi
  views/                    # HTML ulazi i React prikazi
scripts/                    # pomoćni razvojni alati
tests/                      # provjere servisa, infrastrukture i upita
database/                   # lokalni ERA model i generirani rječnik (ignorirano)
```

Tok ovisnosti: naredba/API → DependencyService/factory → service → Unit of Work → DAO interface → asyncpg DAO. SQL i vektorski operatori pripadaju konkretnom DAO-u; servis odlučuje koje kandidate i dokaze vratiti. Transakcije pripadaju Unit of Worku. Struktura prati referentni projekt uz traženi izravni asyncpg pristup; SQLAlchemy se koristi samo za Alembic.

### Odgovornosti triju slojeva

Prezentacijski sloj čine `api` i `commands`: validiraju ulaz, pozivaju servis i pretvaraju rezultat ili aplikacijsku pogrešku u HTTP/MCP/CLI odgovor. `McpServer` upravlja transportom, `LocationTools` alatom, a `MapResource` HTML resursom. Stari `KIDSic.mcp.server:create_app` ostaje podržan.

Poslovni sloj čine `services/interfaces` i `services/concrete`: `SourceRegistrationPlanner` provjerava odabir izvora, `SourceRecordNormalizer` primjenjuje ubrizganu strategiju parsera i čuva pravila identiteta snimke, a `SourceService` koordinira dohvat i atomarni uvoz. Nova shema dodaje se parserom koji implementira `SourceRowParser` i registracijom u sastavljanju, bez promjene petlje normalizacije. `RequestParser` interpretira podatke kataloga koje dohvaća servis; ne poziva bazu.

Podatkovni sloj čine ugovori i implementacije `dao`, vanjski adapteri `integrations` te `db/uow`. SQL ostaje u konkretnim DAO klasama, a HTTP dohvat u CKAN adapteru. UoW ugovori nemaju driver ovisnosti; `asyncpg.py` i `asyncpg_source.py` provode read-only snimku odnosno serijalizirani upis. Driver pogreške prelaze prema servisima kao `PersistenceError`, uz očuvanje uzroka i oslobađanje veze. Postojeća commit/rollback pravila nisu promijenjena.

`factories` i `DependencyService` sastavljaju konkretne implementacije i upravljaju resursima. DTO-i prenose podatke preko granica slojeva. SOLID ovdje znači odvojene razloge promjene, zamjenjive parser strategije, male ugovore čitanja/upisa i constructor injection; čisti pomoćni izračuni ostaju funkcije. `tests/test_architecture.py` provjerava smjer ovisnosti i dodavanje nove sheme bez mijenjanja poslovnog servisa.

## Pokretanje

```sh
uv sync --locked
docker compose up -d --build --wait database
export DATABASE_URL=postgresql://kidsic:kidsic_local@localhost:55432/kidsic
uv run alembic -c src/KIDSic/db/alembic/alembic.ini upgrade head
uv run kidsic-register-sources
uv run kidsic-sync-kindergartens
uv run kidsic-search 'Imam dijete od 2 godine i iz varazdina sam koji su mi vrtici opcija'
```

Naredba pretražuje prethodno uvezene podatke. Bez imenika traži pojašnjenje jer grad nije poznat. Uvoz razlikuje mjesto (npr. Sesvete) od grada/općine (Zagreb) i dodaje kurirane padežne aliase za Zagreb, Varaždin i Rijeku. Upit za grad uključuje i njegova mjesta. `.env.example` je predložak, a `.env` se ne učitava automatski. Postavke `DATABASE_POOL_MIN_SIZE` i `DATABASE_POOL_MAX_SIZE` upravljaju poolom. CLI trenutačno koristi leksički RAG dohvat; servis podržava i predani embedding s oznakom modela.

Migracija `0005_supported_cities` uklanja postojeće ustanove izvan obuhvata,
njihove objekte, izvorne zapise i ovisne podatke. Ustanova s barem jednim
objektom u podržanom gradu ostaje, zajedno s potrebnim identitetom i dokazima,
čak i ako joj je sjedište drugdje. Prije migracije napraviti `pg_dump` baze;
izbrisani podaci mogu se vratiti iz sigurnosne kopije, a downgrade ih ne obnavlja.

## CKAN registracija i uvoz

Vrsta pružatelja obavezno je pohranjena u `kindergarten.provider_kind`:
`municipal` (gradski), `private` (privatni), `childminder` (dadilje),
`religious` (vjerski) i `other` (ostali programi/ustanove). `unknown` ostaje
za nove ustanove čiji tip još nije potvrđen. Objekti preuzimaju tip povezane
ustanove; `location.kind` zasebno razlikuje matični i područni objekt.
API lokacija i razgovorna pretraga vraćaju `provider_kind` uz svaki rezultat.
Nacionalni uvoz dopunjava pregledane vrtiće u Varaždinu i Zagrebu prema
potvrđenom gradu i točnom normaliziranom nazivu, uz poveznicu na izvor
osnivača u provenijenciji. Migracija `0004_provider_kinds` dopunjava postojeće
nepoznate tipove; poznate tipove i identitete zadržava.

Obrazac je preuzet iz [FOIHireloom CKAN integracije](https://github.com/imim77/FOIHireloom/tree/8ba897db799e993aa43c7d488879efb3870218f2/src/FOIHireloom): caller-owned `httpx.AsyncClient`, interface i konkretni klijent, DTO validacija, odvojene HTTP/transport/API/response pogreške, servis, factory, Unit of Work i CLI s `--dry-run`. KIDSic koristi asyncpg za sve upise. MZOM-ov resurs ima tekstualni ID pa DTO prihvaća string umjesto isključivo UUID-a.

Početni izvori:

- `national`: [MZOM — Dječji vrtići](https://data.gov.hr/ckan/dataset/djecji-vrtici), osnovni nacionalni imenik.
- `zagreb-municipal`: [Gradski vrtići — kontakt podaci](https://data.zagreb.hr/dataset/gradski_vrtici_grada_zagreba), matični i područni objekti.
- `zagreb-other`: [Privatni/vjerski vrtići i obrti](https://data.zagreb.hr/dataset/privatni-vjerski-obrti-gz-kontakt-podaci), uz zasebno označene obrte dadilja.
- `varazdin-childminders`: [Grad Varaždin — dadilje](https://data.gov.hr/ckan/dataset/grad-varazdin-dadilje/resource/2bde0eae-1d20-41c5-aec4-711f2a485439), CSV popis obrta za dadilje.

```sh
# Bez DATABASE_URL i bez pristupa bazi:
uv run kidsic-register-sources --dry-run
uv run kidsic-sync-kindergartens --dry-run

# Odabir jednog ili više izvora; bez --source koriste se sva četiri:
uv run kidsic-sync-kindergartens --source national
uv run kidsic-sync-kindergartens --source zagreb-municipal --source zagreb-other
uv run kidsic-sync-kindergartens --source varazdin-childminders --dry-run
uv run kidsic-sync-kindergartens --source varazdin-childminders
```

Registracija poziva `package_show`, traži aktivan resurs zadanog formata (JSON ili CSV) i provjerava `open-license` (Otvorena dozvola). Metapodatke sprema u `data_source`; ponovljena registracija čuva `import_allowed`, aktivnu snimku i povijest. Ne uvozi sadržaj. Sync registrira izvore po potrebi i zasebno preuzima njihove JSON/CSV datoteke; ne pretpostavlja uključen DataStore. Nazivi portala, ID-jevi skupova, timeout i ograničenje veličine odgovora konfiguriraju se `CKAN_*` varijablama iz `.env.example`. Mapiranja su namijenjena ovim četirima shemama. Za varaždinske dadilje dodatno se provjerava točan ID korisnikova CSV resursa; drugi CSV nije automatska zamjena.

Sync provjerava sve odabrane resurse prije transakcije. Sprema izvorne retke u `source_record`, normalizirane ustanove i objekte te podrijetlo polja. MZOM-ov redak opisuje pravnu osobu: njegova adresa sprema se kao sjedište ustanove, a ne kao objekt. Objekte daju zagrebački skupovi; ustanova bez poznatog objekta u pretrazi se prikazuje sa sjedištem (`scope=seat`). Spajanje koristi prethodni identitet izvora, OIB kada postoji te normalizirane nazive, grad/mjesto i adresu; ne koristi neprovjerene približne podudarnosti. Način odluke sprema se u `source_record.match_method`. Višeznačni zapisi ostaju `candidate` za pregled. Sve odabrane snimke aktiviraju se atomarno, a neuspjeh čuva prethodnu aktivnu snimku. Stari retci ostaju u povijesti. Ponovljeni uvoz istih identiteta čuva ID-jeve ustanova i lokacija; pisci se serijaliziraju transakcijskim advisory lockom.

Ovi skupovi nemaju potvrđene dobne uvjete, slobodna mjesta ni upisne upute. Uvoz ih ne izmišlja i ne stvara programe ni RAG dokumente iz kontaktnih podataka. Rezultati zato imaju dobni status `unknown`. Datum preuzimanja i izmjene resursa spremaju se odvojeno; ne proglašavaju se datumom stvarnog stanja podataka.

### Varaždinski obrti za dadilje

Skup iz CKAN API-ja (`package_show`) vodi do CSV datoteke: DataStore nije uključen. CSV se čita kao UTF-8 s mogućim BOM-om, razdjelnikom `;` i navodnicima. Prazni retci se preskaču, a neispravan broj stupaca, kodiranje ili obvezna polja prekidaju uvoz prije upisa. Vrijede isto ograničenje veličine odgovora i obrada HTTP pogrešaka kao za JSON izvore.

Spremaju se naziv, adresa sjedišta, mjesto i poštanski broj, vrsta `childminder`, kontaktni telefon, e-mail, web/Facebook poveznica i jednoznačan OIB. `Matični broj` obrta je stabilan `source_record.source_key`, pa promjena adrese ili kontakta ne stvara novi obrt. Cijeli izvorni redak ostaje u `source_record.raw_data`, zajedno s vezom na izvor, licencijom i datumom preuzimanja. Imena odgovornih osoba ne dodaju se kao zasebna polja ustanove. Ako redak navodi više OIB-a, svi ostaju u izvornom retku, a jedinstveni `kindergarten.oib` ostaje prazan.

Stupci su označeni kao adrese sjedišta; ne proglašavaju se fizičkim objektima za čuvanje djece. Skup nema koordinate, kvartove, dobne uvjete ni podatke o slobodnim mjestima. Uvoz ne stvara takve podatke ni RAG dokumente iz kontakata. Obrti su dostupni u imeniku i pretrazi kao `childminder`, sa sjedištem i nepoznatom dobnom prikladnošću. API lokacija podržava `provider_kind=childminder`; bez koordinata nema oznake na karti.

Dodatno geokodiranje sjedišta nalazi se u `data-enrichment/varazdin-childminders-nominatim.json` i uvozi naredbom `uv run python data-enrichment/import_childminder_geography.py --apply`. Revizija `0003_seat_geography` dodaje `seat_longitude`, `seat_latitude` i `seat_attributes` postojećoj tablici `kindergarten`. Provjera izvora i podudaranja trenutačne adrese objedinjena je u pogledu `kindergarten_seat_geography`. Poznati kvartovi, predjeli, susjedstva i naselja koriste se za filtriranje pretrage prije RAG dohvaćanja; geografski dokumenti ostaju odvojeni od dokaza dobne prikladnosti.

## Lokalni pregled MCP sučelja

API se pokreće nad prethodno migriranom i popunjenom bazom iz koraka iznad:

```sh
uv run uvicorn KIDSic.api.locations:create_app --factory --host 127.0.0.1 --port 8000
```

`DATABASE_URL` mora biti postavljen u istom terminalu. API drži jedan pool kroz životni vijek aplikacije; svaki zahtjev čita konzistentnu snimku kroz read-only Unit of Work. Pokretanje ne izvršava migracije ni uvoz. [Ugovor lokacija](LOCATION_API.md) opisuje `GET /api/locations`, filtre, GeoJSON, izvore, datume i pogreške. Dobno filtrirana razgovorna pretraga ostaje zaseban servis.

Frontend pokrenuti u drugom terminalu:

```sh
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

U `frontend/.env.local` postaviti javni `VITE_MAPBOX_ACCESS_TOKEN=pk.…` iz Mapbox računa. Koristiti namjenski javni token s dopuštenim razvojnim i produkcijskim URL-ovima. Vite ugrađuje `VITE_*` vrijednosti u klijentski kod: token je vidljiv korisniku, a tajni `sk.*` token ne pripada frontendu. `.env.local` je ignoriran; nakon promjene ponovno pokrenuti Vite, a za produkciju ponovno izgraditi frontend.

Vite služi `src/views/index.html`, učitava env iz mape `frontend/` i prosljeđuje `/api` lokalnom API-ju na portu 8000. Produkcijski samostalni hosting mora usmjeriti `/api` na isti backend; razvojni proxy nije dio statičkog builda. Zajednički resursi su u `src/shared`. MCP prikaz koristi zaseban samostalni HTML build i rezultate alata preko host bridgea, bez HTTP dohvata iz iframea; [upute za MCP povezivanje](MCP.md).

Ako je port 8000 zauzet, API pokrenuti s `--port 18000`, a frontend naredbom `KIDSIC_API_TARGET=http://127.0.0.1:18000 npm run dev`. `KIDSIC_API_TARGET` je varijabla procesa koji pokreće Vite, ne javna varijabla aplikacije iz `.env.local`.

UI prikazuje kartu s vodoravno pomičnim karticama, odabirom objekta i kontrolom za fullscreen. Navigacija i filtri uklonjeni su iz samog prikaza; kompaktna legenda objašnjava boje pružatelja: zelena javne i ostale, ljubičasta privatne, narančasta vjerske i ružičasta dadilje; razvojni dohvat koristi Zagreb kao početni kontekst, a API i dalje prihvaća dokumentirane strukturirane kriterije. Sjedišta i objekti bez koordinata ostaju među karticama. Sjedišta s provjerenim geokodiranjem imaju oznaku na karti, zadržavaju `location_role=seat` i na kartici nose oznaku „Sjedište”. Odabir kartice otvara detalje s tipom pružatelja i dostupnim kontaktima: webom, e-mailom i telefonom. Google karte i izvori nisu prikazani u detaljima; izvori ostaju u API-ju. Odabrana točka na karti zadržava boju tipa pružatelja, uz veći radijus i obrub. Dobna prikladnost, slobodna mjesta i kapacitet ne zaključuju se iz lokacije. Bez Mapbox tokena ili podržanog WebGL-a dostupne su kartice stvarnih rezultata. Prazna baza daje prazan rezultat, a nedostupan API poruku za ponovni pokušaj; aplikacija ne prikazuje zamjenske izmišljene objekte.

## Provjere i dokumentacija

```sh
uv run python -m unittest discover -s tests -v
```

Frontend provjere iz mape `frontend/`: `npm test`, `npm run build` i `npm run lint`. Testovi komponenti provjeravaju lifecycle karte, potpune odgovore i otkazivanje zastarjelih zahtjeva s izoliranim Mapbox mockom; stvarni prikaz podloge treba provjeriti u pregledniku s javnim tokenom.

Integracijske provjere trebaju zasebnu, migriranu bazu `kidsic_test_*` i `KIDSIC_TEST_DATABASE_URL`. Bez te varijable integracijski testovi se preskaču. Detalji: [baza i RAG](database/README.md), [ERA model](database/ERA.md), [funkcionalnosti](TO-DO.md).

Testovi CKAN klijenta i normalizacije rade offline. Testovi uvoza nad PostgreSQL-om provjeravaju ponovljivost, povijest, povezivanje izvora, nepoznatu dob i rollback. [Lokalna Postman simulacija](postman/README.md) dodatno provjerava stvarni HTTP promet, timeout i pogreške bez vanjskih servisa; uključuje se varijablom `KIDSIC_CKAN_SIMULATION_URL`.

Lokalno istraživanje u `docs/`, dokumentacija baze u `database/` i pomoćne skripte u `scripts/` ne ulaze u Git. Razvojni rezultati, `.env`, `.venv` i `node_modules` također su ignorirani. Commits slijede Conventional Commits (`chore`, `feat`, `test`, `docs` s odgovarajućim scopeom).
