# KIDSic

MCP app za pronalazak dječjih vrtića povezivanjem više otvorenih skupova. Implementirani su PostgreSQL model, CKAN registracija i uvoz imenika, objekata, kontakata te povijesnih zagrebačkih programa i mjesta. MCP alat `prikazi_vrtice` povezuje obavezan grad s OpenStreetMap kartom i karticama. `dohvati_kontekst_vrtica` dohvaća podatke za razgovorne odgovore s izvorima, datumima i opsegom. RAG vraća sve prihvaćene dokaze odabranih tema za odabrani vrtić, bez rangiranja i embedding pružatelja. Odgovor sastavlja model MCP klijenta.

Aplikacija podržava samo **Zagreb, Varaždin, Rijeku i Šibenik**. Uvoz preskače zapise
iz drugih gradova prije upisa u bazu; pripadnost gradu određuje se prema
potvrđenoj općini, pa zagrebačka naselja poput Sesveta ostaju uključena.
HTTP API odbija nepodržani grad statusom 422, a MCP alat vraća popis podržanih
gradova. Razgovorna pretraga koristi isti obuhvat.

## Brzi početak i povezivanje s AI klijentom

### 1. Priprema i lokalno pokretanje

Potrebni su Git, Docker s Composeom i pokrenutim Docker servisom, `uv`,
Node.js i npm te internetska veza. Projekt zahtijeva Python 3.14 ili noviji;
`uv` može preuzeti odgovarajuću verziju. Na Windowsu je preporučen WSL2.

Klonirajte repozitorij, uđite u njegov direktorij i izvršite:

```sh
uv sync --locked
npm --prefix frontend ci
docker compose up -d --build --wait database
export DATABASE_URL=postgresql://kidsic:kidsic_local@localhost:55432/kidsic
uv run alembic -c src/KIDSic/db/alembic/alembic.ini upgrade head
uv run kidsic-register-sources
uv run kidsic-sync-kindergartens
npm --prefix frontend run build:mcp
uv run uvicorn KIDSic.api.mcp_server:create_app --factory --host 127.0.0.1 --port 8001
```

Ostavite terminal otvoren. MCP server dostupan je na
`http://127.0.0.1:8001/mcp`; `DATABASE_URL` vrijedi u tom terminalu.
Prvi uvoz dohvaća stvarne podatke s CKAN portala i ovisi o njihovoj
dostupnosti. Repozitorij zasad **ne sadrži automatski obnovljivu snimku naše
popunjene baze**, pa dio ručno pregledanih geografskih dopuna neće biti
prisutan. Za upisne dokumente nakon uvoza imenika u drugom terminalu uz isti
`DATABASE_URL` pokrenite `uv run kidsic-sync-enrolment`. Za rute je potrebna
zasebna priprema OpenTripPlannera i adresnih indeksa.

Ako samo želite pregledati kartu u pregledniku, slijedite korake pod
[Lokalni pregled MCP sučelja](#lokalni-pregled-mcp-sučelja). Za zaustavljanje
MCP servera pritisnite `Ctrl+C`, a bazu zaustavite s `docker compose down`;
podaci ostaju u Docker volumenu.

### 2. Omogućite pristup MCP serveru

ChatGPT i Claudeovi udaljeni konektori ne pristupaju adresi `127.0.0.1` na
vašem računalu. Dok je lokalni server pokrenut, upotrijebite HTTPS razvojni
tunel ili postavite server na javno dostupan HTTPS hosting. U konektor se
unosi puna adresa s putanjom `/mcp`, primjerice
`https://vasa-adresa.example/mcp`. ChatGPT nudi i
[Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
za podržane račune i okruženja.

KIDSic trenutačno nema ugrađenu autentikaciju za javni endpoint. Prije javnog
izlaganja postavite odgovarajuću zaštitu pristupa i provjerite postavke tunela
ili hostinga. Render deployment i automatsko obnavljanje snimke zasad su plan,
a ne dio postojećeg postupka.

### 3. Povežite ChatGPT ili Claude

**ChatGPT:** otvorite [Plugins](https://chatgpt.com/plugins), odaberite `+` i
`Add custom MCP server`. Unesite naziv i HTTPS adresu koja završava s `/mcp`
(ili odaberite podržani Secure MCP Tunnel), konfigurirajte autentikaciju i
izradite plugin. Instalirajte ga, započnite novi razgovor i odaberite ga s
`@`. Dostupnost i dopuštenja ovise o računu i radnom prostoru. Detalji su u
[OpenAI uputama](https://developers.openai.com/plugins/build/app-quickstart).

**Claude:** u `Customize → Connectors` odaberite `+ Add → Add custom connector`,
unesite naziv i javnu HTTPS adresu s `/mcp`, pregledajte autentikaciju i
dodajte konektor. U razgovoru ga uključite kroz izbornik konektora. Za Team i
Enterprise konektor može trebati dodati administrator. Detalji su u
[Claudeovim uputama](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp).

Zatim pokušajte: **„Prikaži mi vrtiće u Zagrebu na karti.”** Za interaktivnu
kartu klijent mora podržavati MCP Apps; klijent koji podržava samo MCP alate
može koristiti rezultate alata bez prikaza karte. Mogu se koristiti i drugi
kompatibilni MCP klijenti, uključujući lokalne razvojne klijente. Njihov
postupak povezivanja i podrška za interaktivni prikaz ovise o klijentu.


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
  pages/                    # HTML ulazi
  mvvm/                     # React MVVM: zajednički UI, hookovi i značajke
scripts/                    # uvoz ručno pregledane geografije
tests/                      # provjere servisa, infrastrukture i upita
database/                   # lokalni ERA model i generirani rječnik (ignorirano)
```

Tok ovisnosti: naredba/API → DependencyService/factory → service → Unit of Work → DAO interface → asyncpg DAO. SQL i vektorski operatori pripadaju konkretnom DAO-u; servis odlučuje koje kandidate i dokaze vratiti. Transakcije pripadaju Unit of Worku. Struktura prati referentni projekt uz traženi izravni asyncpg pristup; SQLAlchemy se koristi samo za Alembic.

### Odgovornosti triju slojeva

Prezentacijski sloj čine `api` i `commands`: validiraju ulaz, pozivaju servis i pretvaraju rezultat ili aplikacijsku pogrešku u HTTP/MCP/CLI odgovor. `McpServer` upravlja transportom, `LocationTools` alatom, a `MapResource` HTML resursom. Stari `KIDSic.mcp.server:create_app` ostaje podržan.

Poslovni sloj čine `services/interfaces` i `services/concrete`: `SourceRegistrationPlanner` provjerava odabir izvora, `SourceRecordNormalizer` primjenjuje ubrizganu strategiju parsera i čuva pravila identiteta snimke, a `SourceService` koordinira dohvat i atomarni uvoz. Nova shema dodaje se parserom koji implementira `SourceRowParser` i registracijom u sastavljanju, bez promjene petlje normalizacije.

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
```

Uvoz razlikuje mjesto (npr. Sesvete) od grada/općine (Zagreb) i dodaje kurirane padežne aliase za Zagreb, Varaždin, Rijeku i Šibenik. Upit za grad uključuje i njegova mjesta. `.env.example` je predložak, a `.env` se ne učitava automatski. Pool baze ima fiksno 1–10 veza.

Migracija `0005_supported_cities` uklanja postojeće ustanove izvan obuhvata,
njihove objekte, izvorne zapise i ovisne podatke. Ustanova s barem jednim
objektom u podržanom gradu ostaje, zajedno s potrebnim identitetom i dokazima,
čak i ako joj je sjedište drugdje. Prije migracije napraviti `pg_dump` baze;
izbrisani podaci mogu se vratiti iz sigurnosne kopije, a downgrade ih ne obnavlja.

Migracija `0020_croatian_columns` preimenuje stupce aplikacijskih tablica i
pogleda na hrvatski bez zamjene podataka. Primjenjuje se naredbom
`uv run alembic -c src/KIDSic/db/alembic/alembic.ini upgrade head`.
DAO upiti koriste hrvatske nazive, a izlaznim aliasima zadržavaju postojeće
DTO i API ugovore. JSON ključevi izvornih podataka ostaju nepromijenjeni.

## CKAN registracija i uvoz

Vrsta pružatelja obavezno je pohranjena u `vrtici.vrsta_pruzatelja`:
`municipal` (gradski), `private` (privatni), `childminder` (dadilje),
`religious` (vjerski) i `other` (ostali programi/ustanove). `unknown` ostaje
za nove ustanove čiji tip još nije potvrđen. Objekti preuzimaju tip povezane
ustanove; `objekti.vrsta` zasebno razlikuje matični i područni objekt.
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
- `rijeka-kindergartens`: [Grad Rijeka — dječji vrtići](https://data.rijeka.hr/dataset/djecji-vrtici), CSV pojedinačnih objekata i njihovih ustanova/osnivača.

```sh
# Bez DATABASE_URL i bez pristupa bazi:
uv run kidsic-register-sources --dry-run
uv run kidsic-sync-kindergartens --dry-run

# Odabir jednog ili više izvora; bez --source koristi se svih pet:
uv run kidsic-sync-kindergartens --source national
uv run kidsic-sync-kindergartens --source zagreb-municipal --source zagreb-other
uv run kidsic-sync-kindergartens --source varazdin-childminders --dry-run
uv run kidsic-sync-kindergartens --source varazdin-childminders
uv run kidsic-sync-kindergartens --source rijeka-kindergartens --dry-run
uv run kidsic-sync-kindergartens --source rijeka-kindergartens

# Tek nakon pregleda potpunosti izvora i opravdanosti nestalih ključeva:
uv run kidsic-sync-kindergartens --source national --allow-removals
```

Registracija poziva `package_show`, traži aktivan resurs zadanog formata (JSON ili CSV) i provjerava očekivanu licencu po izvoru: `open-license` (Otvorena dozvola), odnosno `cc-by` za Rijeku. Metapodatke sprema u `izvori_podataka`; ponovljena registracija čuva `import_allowed` i trenutačno stanje. Ne uvozi sadržaj. Sync registrira izvore po potrebi i zasebno preuzima njihove JSON/CSV datoteke; ne pretpostavlja uključen DataStore. Nazivi portala, ID-jevi skupova, timeout i ograničenje veličine odgovora konfiguriraju se `CKAN_*` varijablama iz `.env.example`. Mapiranja su namijenjena ovim pet shemama. Za varaždinske dadilje i riječke objekte dodatno se provjerava točan ID CSV resursa; drugi CSV nije automatska zamjena.

Sync provjerava sve odabrane resurse prije transakcije. Sprema izvorne retke u `izvorni_zapisi`, normalizirane ustanove i objekte te podrijetlo polja. MZOM-ov redak opisuje pravnu osobu: njegova adresa sprema se kao sjedište ustanove, a ne kao objekt. Objekte daju zagrebački i riječki skupovi; ustanova bez poznatog objekta u pretrazi se prikazuje sa sjedištem (`location_role=seat`). Spajanje koristi prethodni identitet izvora, OIB kada postoji te normalizirane nazive, grad/mjesto i adresu; ne koristi neprovjerene približne podudarnosti. Način odluke sprema se u `izvorni_zapisi.metoda_povezivanja`. Višeznačni zapisi ostaju `candidate` za pregled. Trenutačno stanje svih odabranih izvora zamjenjuje se atomarno, a neuspjeh čuva prethodne podatke. Ponovljeni uvoz istih identiteta čuva ID-jeve izvornih zapisa, ustanova i lokacija; pisci se serijaliziraju transakcijskim advisory lockom.

Ako nedostaje ijedan prethodni `source_key`, sync odbija cijeli uvoz uz naziv
izvora, broj i uzorak nestalih ključeva. Provjerite potpunost datoteke i razlog
uklanjanja prije ponavljanja s `--allow-removals`, po mogućnosti za jedan
`--source`. Ta opcija dopušta brisanje nestalih zapisa i izvedenih redaka;
prazni i duplicirani skupovi i dalje su zabranjeni. Promjena ključa također
traži pregled, čak i uz jednak broj redaka. `--dry-run` ne pristupa bazi pa
ne uspoređuje ključeve s prethodnim stanjem. Provjera ne dokazuje potpunost
prvog uvoza ni sadržaja pojedinog retka.

Baza čuva samo trenutačni sadržaj tih izvornih zapisa. Stabilan ID nije
nepromjenjiva verzija dokaza. Dump omogućuje obnovu eksplicitno spremljenog
trenutka; potpuna povijest izvora i reprodukcija svih ranijih odgovora nisu
implementirane.

Ovi skupovi nemaju potvrđene dobne uvjete, slobodna mjesta ni upisne upute. Uvoz ih ne izmišlja i ne stvara programe ni RAG dokumente iz kontaktnih podataka. Datum preuzimanja i izmjene resursa spremaju se odvojeno; ne proglašavaju se datumom stvarnog stanja podataka.

### Povijesni zagrebački programi i slobodna mjesta

Zaseban uvoz preko istog HTTP/CKAN klijenta koristi tri resursa pod Otvorenom
dozvolom (OD):

- [Programi po objektima, XLSX objavljen 9. 10. 2019.](https://data.zagreb.hr/dataset/djecji-vrtici-grada-zagreba/resource/b94a968b-be3a-410b-84d3-2e5a857b311d)
- [Slobodna mjesta u gradskim vrtićima, stanje 1. 1. 2025.](https://data.zagreb.hr/dataset/slobodna-mjesta-u-vrticima-i-obrtima-za-cuvanje-djece-grada-zagreba/resource/a6a9199d-eaf4-4f75-9bce-7a3a5b367d30)
- [Slobodna mjesta kod dadilja, stanje 1. 1. 2025.](https://data.zagreb.hr/dataset/slobodna-mjesta-u-vrticima-i-obrtima-za-cuvanje-djece-grada-zagreba/resource/f1c42d5e-17c8-40e9-83a9-fba7539bd4b5)

```bash
uv run alembic -c src/KIDSic/db/alembic/alembic.ini upgrade head
uv run kidsic-sync-historical --dry-run
uv run kidsic-sync-historical
# Opcionalno jedan izvor:
uv run kidsic-sync-historical --source zagreb-programs-2019
```

Prvo uvezite postojeći imenik (`national`, `zagreb-municipal`, `zagreb-other`).
Povijesni uvoz ne stvara nove ustanove, objekte ni koordinate. `povijesni_zapisi`
čuva izvorni redak, datum, programe i mjesta; jednoznačno povezuje nazive unutar
Zagreba, a za programe i adresu objekta. Nepovezani i višeznačni retci ostaju
`candidate` za pregled. `accepted` zapisi dopuštenog izvora pojavljuju se
u detaljima odgovarajućih vrtića kroz `historical_data`. Broj mjesta odnosi se
na cijelu ustanovu/obrt, ne pojedini objekt; ne zbraja se po podružnicama.
Zbrojni stupci CSV-a nisu dodatne skupine. Nula ostaje nula, prazno ostaje nepoznato,
a `/` u programima nije naziv programa ni dokaz da program ne postoji.

Datumi podataka odvojeni su od datuma preuzimanja i izmjene kataloga. Promjena
licence, datuma snimke ili zaglavlja zaustavlja uvoz za pregled. Sve datoteke
provjeravaju se prije transakcije; pogreška zadržava prethodnu snimku. Ponovljeni
uvoz ažurira zapise uz stabilne ID-jeve i uklanja nestale ključeve; stare verzije
uvoza ne čuvaju se. Povijesni datumi, programi i mjesta ostaju u sadržaju. Ti zapisi
ne potvrđuju aktualnu dobnu prikladnost, današnja slobodna mjesta ni pravo upisa.
Iz ovog skupa nema podataka o slobodnim mjestima privatnih i vjerskih vrtića.

### Upisni dokumenti

`kidsic-sync-enrolment` uvozi pregledanu snimku službenih upisnih dokumenata
([2026-11-05_zagreb_enrolment.json](src/KIDSic/db/seeds/2026-11-05_zagreb_enrolment.json))
kao RAG odlomke teme `document`. Opis izvora, licenci i opsega je u
[seeds/README.md](src/KIDSic/db/seeds/README.md#upisni-dokumenti).

```bash
uv run kidsic-sync-enrolment --dry-run
uv run kidsic-sync-enrolment
```

Uvoz ide nakon imenika. Ne stvara ustanove ni objekte i ne šalje mrežne zahtjeve.

### Riječki objekti vrtića

Primarni katalog Grada Rijeke daje CSV resurs
`7fe927d4-16e5-4255-b255-249f7ced3c2c` pod licencom CC-BY. CSV koristi
Windows-1250 i `;`; kodiranje je izričito zadano samo ovom izvoru, bez
nagađanja ili promjene UTF-8 pravila varaždinskog izvora. Katalog `https://data.rijeka.hr`, skup `djecji-vrtici` i resurs su fiksni u
kodu.

Stupci `Vrtić` i `Adresa` opisuju objekt, a `Centar` njegovu ustanovu.
`Osnivač` određuje pregledani tip pružatelja: gradski, privatni ili vjerski;
novi nepoznati osnivač ostaje `unknown`. Cijeli redak, uključujući adresu
centra, ostaje u `izvorni_zapisi.izvorni_podaci`; uvoz objekta ne mijenja sjedište
iz MZOM-a. Lokalni naziv Mala vila povezuje se s punim MZOM nazivom
`Dječji vrtić "Mala Vila", waldorfski`. KBC Rijeka povezuje se s Dječjim
vrtićem Rijeka prema [službenom opisu Grada](https://www.rijeka.hr/gradska-uprava/ustanove/ustanove-odgoju-skolstvu/djecji-vrtici/),
bez stvaranja zasebne vrtićke ustanove KBC.

Identitet retka računa se iz normaliziranih naziva ustanove i objekta;
`RBR` je redni broj, pa promjena redoslijeda ili adrese ne stvara novi objekt.
CSV trenutačno sadrži 50 objekata. Nema koordinate, kontakte ni oznaku
matičnog/područnog objekta: kontakti se prikazuju iz postojeće ustanove ako
postoje, a objekti bez koordinata dostupni su u popisu bez oznake na karti.
Skup ima starije objekte; datum izmjene resursa ne potvrđuje aktualnost
svakog retka. Uvoz ne provodi geokodiranje.

Jednokratno pregledana geografija za 27 riječkih objekata nalazi se u
lokalnoj snimci koju uvozi `scripts/import_rijeka_geography.py`.
Za ostala 23 objekta nije prihvaćeno dovoljno precizno OSM podudaranje.
Upis čuva postojeće identitete i kontakte, a promjena CSV adrese poništava
primjenjivost starog geografskog dokaza do novog pregleda.

### Varaždinski obrti za dadilje

Skup iz CKAN API-ja (`package_show`) vodi do CSV datoteke: DataStore nije uključen. CSV se čita kao UTF-8 s mogućim BOM-om, razdjelnikom `;` i navodnicima. Prazni retci se preskaču, a neispravan broj stupaca, kodiranje ili obvezna polja prekidaju uvoz prije upisa. Vrijede isto ograničenje veličine odgovora i obrada HTTP pogrešaka kao za JSON izvore.

Spremaju se naziv, adresa sjedišta, mjesto i poštanski broj, vrsta `childminder`, kontaktni telefon, e-mail, web/Facebook poveznica i jednoznačan OIB. `Matični broj` obrta je stabilan `izvorni_zapisi.kljuc_izvornog_zapisa`, pa promjena adrese ili kontakta ne stvara novi obrt. Cijeli izvorni redak ostaje u `izvorni_zapisi.izvorni_podaci`, zajedno s vezom na izvor, licencijom i datumom preuzimanja. Imena odgovornih osoba ne dodaju se kao zasebna polja ustanove. Ako redak navodi više OIB-a, svi ostaju u izvornom retku, a jedinstveni `vrtici.oib` ostaje prazan.

Stupci su označeni kao adrese sjedišta; ne proglašavaju se fizičkim objektima za čuvanje djece. Skup nema koordinate, kvartove, dobne uvjete ni podatke o slobodnim mjestima. Uvoz ne stvara takve podatke ni RAG dokumente iz kontakata. Obrti su dostupni u imeniku i pretrazi kao `childminder`, sa sjedištem i nepoznatom dobnom prikladnošću. API lokacija podržava `provider_kind=childminder`; bez koordinata nema oznake na karti.

Dodatno geokodiranje sjedišta nalazi se u `scripts/varazdin-childminders-nominatim.json` i uvozi naredbom `uv run python scripts/import_childminder_geography.py --apply`. Geografija se od revizije `0013_kindergarten_seat` čuva uz sjedište u `sjedista_vrtica`, s FK-om na izvorni zapis. Provjera izvora i podudaranja trenutačne adrese objedinjena je u pogledu `kindergarten_seat_geography`. Poznati kvartovi, predjeli, susjedstva i naselja koriste se za filtriranje pretrage prije RAG dohvaćanja; geografski dokumenti ne potvrđuju dobnu prikladnost.

## Lokalni pregled MCP sučelja

API se pokreće nad prethodno migriranom i popunjenom bazom iz koraka iznad:

```sh
uv run uvicorn KIDSic.api.locations:create_app --factory --host 127.0.0.1 --port 8000
```

`DATABASE_URL` mora biti postavljen u istom terminalu. API drži jedan pool kroz životni vijek aplikacije; svaki zahtjev čita konzistentnu snimku kroz read-only Unit of Work. Pokretanje ne izvršava migracije ni uvoz. HTTP API opisuje `GET /api/locations`, filtre, GeoJSON, izvore, datume i pogreške. MCP karta podržava grad, naziv, vrstu pružatelja, područje i radijus; alat za RAG kontekst koristi zaseban servis nad istim poolom.

Frontend pokrenuti u drugom terminalu:

```sh
cd frontend
npm ci
npm run dev
```

Karta koristi Leaflet i OpenStreetMap pločice bez API tokena. Potrebna je internetska veza za dohvat podloge; atribucija OpenStreetMap suradnika prikazana je na karti.

Vite služi `src/pages/index.html`, učitava env iz mape `frontend/` i prosljeđuje `/api` lokalnom API-ju na portu 8000. Produkcijski samostalni hosting mora usmjeriti `/api` na isti backend; razvojni proxy nije dio statičkog builda. Kod prikaza je u `src/mvvm` (Container → ViewModel → View). MCP prikaz koristi zaseban samostalni HTML build i rezultate alata preko host bridgea, bez HTTP dohvata iz iframea.

Ako je port 8000 zauzet, API pokrenuti s `--port 18000`, a frontend naredbom `KIDSIC_API_TARGET=http://127.0.0.1:18000 npm run dev`. `KIDSIC_API_TARGET` je varijabla procesa koji pokreće Vite, ne javna varijabla aplikacije iz `.env.local`.

UI prikazuje kartu s vodoravno pomičnim karticama, odabirom objekta i kontrolom za fullscreen. Navigacija i filtri uklonjeni su iz samog prikaza; kompaktna legenda objašnjava boje pružatelja: zelena javne i ostale, ljubičasta privatne, narančasta vjerske i ružičasta dadilje; razvojni dohvat koristi Zagreb kao početni kontekst, a API i dalje prihvaća dokumentirane strukturirane kriterije. Sjedišta i objekti bez koordinata ostaju među karticama. Sjedišta s provjerenim geokodiranjem imaju oznaku na karti, zadržavaju `location_role=seat` i na kartici nose oznaku „Sjedište”. Odabir kartice otvara detalje s tipom pružatelja i dostupnim kontaktima: webom, e-mailom i telefonom. Google karte i izvori nisu prikazani u detaljima; izvori ostaju u API-ju. Odabrana točka na karti zadržava boju tipa pružatelja, uz veći radijus i obrub. Dobna prikladnost, slobodna mjesta i kapacitet ne zaključuju se iz lokacije. Ako podlogu nije moguće učitati, dostupne su kartice stvarnih rezultata. Karta ne zahtijeva WebGL ni Web Workere. Prazna baza daje prazan rezultat, a nedostupan API poruku za ponovni pokušaj; aplikacija ne prikazuje zamjenske izmišljene objekte.

## Provjere i dokumentacija

```sh
uv run python -m unittest discover -s tests -v
```

Frontend provjere iz mape `frontend/`: `npm test`, `npm run build` i `npm run lint`. Testovi komponenti provjeravaju lifecycle karte, potpune odgovore i otkazivanje zastarjelih zahtjeva s Leaflet kartom; stvarni dohvat OpenStreetMap podloge treba provjeriti u pregledniku.

Integracijske provjere trebaju zasebnu, migriranu bazu `kidsic_test_*` i `KIDSIC_TEST_DATABASE_URL`. Bez te varijable integracijski testovi se preskaču. Lokalna dokumentacija baze i ERA model dostupni su u mapi `database/` kada je pripremljena.

Testovi CKAN klijenta i normalizacije rade offline. Testovi uvoza nad PostgreSQL-om provjeravaju stabilne identitete, zamjenu stanja, povijesne objave, obuhvat dokumenata, povezivanje izvora i rollback. [Lokalna Postman simulacija](postman/README.md) dodatno provjerava stvarni HTTP promet, timeout i pogreške bez vanjskih servisa; uključuje se varijablom `KIDSIC_CKAN_SIMULATION_URL`.

Lokalno istraživanje u `docs/`, dokumentacija baze u `database/`, `scripts/export_database_model.py` i lokalne JSON snimke u `scripts/` ne ulaze u Git. Razvojni rezultati, `.env`, `.venv` i `node_modules` također su ignorirani. Commits slijede Conventional Commits (`chore`, `feat`, `test`, `docs` s odgovarajućim scopeom).


### Vrtići na putu do posla: Rijeka, Zagreb i Šibenik

MCP alat `preporuci_vrtice_usput` uspoređuje dom → vrtić → posao za sva tri grada.
Zagreb koristi službeni ZET GTFS pod Otvorenom dozvolom RH, zaseban lokalni
OpenTripPlanner i OSM adresni indeks. Raspored za Zagreb: 21. 10. – 31. 12. 2026.


Šibenik koristi službeni GTFS Gradskog parkinga pod Otvorenom dozvolom RH,
sa zasebnim OTP-om i adresnim indeksom. Raspored: 7. 9. 2026. – 7. 6. 2027.
Nacionalni imenik sadrži šest šibenskih/brodaričkih ustanova; šibenska Hozana
povezana je sa zagrebačkim sjedištem. Za rute su trenutačno provjerena **tri
OSM objekta**: Šibenski tići, Vidici i Blažena Hozana. To nije potpun popis
objekata. Sjedišta bez potvrđenog objekta ne ulaze u rangiranje. Programi,
radno vrijeme, cijene i slobodna mjesta nisu preuzeti s nelicenciranih stranica.
Šibenske podatke obrađuje `scripts/import_sibenik.py`.

Rekonstrukcija sheme: prije migracija 0009–0013 spremiti `pg_dump -Fc`.
Migracija 0010 uklanja stare snimke izvora i čuva ID postojećeg zapisa pri
ponovnom uvozu. Povijesni programi i mjesta ostaju u `historical_record`.
Migracija 0011 uklanja dotadašnje upisne kopije; odmah zatim pokrenuti
`uv run kidsic-sync-enrolment` iz pregledanih seedova. Opći dokument vrijedi
prema gradu i vrstama pružatelja, uključujući kasnije dodane ustanove; imenovani
odlomci i odbijanja ostaju ograničeni na navedene ustanove. Downgrade vraća
shemu, a izbrisani sadržaj vraća se iz dumpa ili ponovnim uvozom.

Migracija 0013 izdvaja sjedišta u `kindergarten_seat`; županija dolazi iz
`municipality`, a geografija se koristi samo uz istu adresu i aktivan dokaz.

Migracija 0012 uklanja aktualne programe i pripadajuće filtre. `prikazi_vrtice`
i HTTP više ne prihvaćaju `age_months`, `program` ni `include_unknown`;
`kidsic-search` je uklonjen. Tema `programs` u RAG-u i `historical_data.programs`
čuvaju isključivo povijesne objave, bez potvrde današnje provedbe ili dobi.

Migracija 0014 uklanja nečitani trigram indeks i `pg_trgm`, generirani
`location.position`, hash odlomka `knowledge_chunk.content_sha256` i prazna
sjedišta. Prostorni upiti i dalje koriste PostGIS nad koordinatama.

Migracija 0017 uklanja `source_record.batch_id`, `historical_record.batch_id` i
`data_source.active_batch_id`. Povijesni uvoz sada zamjenjuje trenutačno stanje
prema `(source_id, source_key)`. Migracija briše neaktivne povijesne verzije,
a neaktivne izvorne zapise odbija radi pregleda njihova provenancea. Prije
primjene spremiti `pg_dump -Fc`; downgrade vraća jednu tehničku snimku po izvoru,
a ranije verzije uvoza mogu se obnoviti samo iz dumpa. API više ne izlaže
`field_sources.*.active_snapshot`, a rezultat CKAN uvoza nema `batch_id`.

Migracija 0018 dodaje `document_record` za obvezni `reference_date`, vrstu datuma
`date_kind` i opcionalni `valid_until`. Baza provjerava vrstu datuma i redoslijed
razdoblja. Vrsta izvora je u `data_source.kind` (`general` ili
`enrolment_document`), obuhvat u `document_scope`, a URL u `data_source.url`.
Premješteni aplikacijski ključevi uklanjaju se iz `raw_data`; izvorni sadržaj
ostaje očuvan, a tekst dokumenata ostaje u `knowledge_chunk`. `snapshot_key`
ostaje u metapodacima izvora. Prije migracije spremiti `pg_dump -Fc`;
proturječni URL-ovi, datumi, oznake snimki ili obuhvati zahtijevaju pregled.
Downgrade vraća JSON ugovor iz tipiziranih podataka. Javni rezultati alata i
kartice ostaju isti.

Migracija 0019 preimenuje aplikacijske tablice na hrvatski, u množini.
Nazivi stupaca, pogleda, indeksa i ograničenja ostaju isti, kao i javni API.
Podaci i identiteti ostaju očuvani; downgrade vraća stare nazive.

| Prijašnji naziv | Aktualni naziv |
| --- | --- |
| `data_source` | `izvori_podataka` |
| `source_record` | `izvorni_zapisi` |
| `kindergarten` | `vrtici` |
| `kindergarten_seat` | `sjedista_vrtica` |
| `location` | `objekti` |
| `municipality` | `jedinice_lokalne_samouprave` |
| `municipality_subsidy_policy` | `pravila_sufinanciranja` |
| `enrolment` | `upisni_krugovi` |
| `enrolment_refusal` | `neprihvacanja_upisa` |
| `document_scope` | `obuhvati_dokumenata` |
| `document_record` | `zapisi_dokumenata` |
| `knowledge_chunk` | `odlomci_znanja` |
| `historical_record` | `povijesni_zapisi` |

`alembic_version` i PostGIS tablica `spatial_ref_sys` zadržavaju izvorne nazive.
Prije nadogradnje napraviti `pg_dump -Fc`; u PyCharmu nakon nje osvježiti
shemu `public` da prikaz učita nove nazive.
