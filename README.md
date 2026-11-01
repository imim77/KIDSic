# KIDSic

MCP app u razvoju za pronalazak dječjih vrtića povezivanjem više otvorenih skupova. Implementirani su PostgreSQL model, CKAN registracija izvora i uvoz triju JSON skupova, SQL pretraga prema gradu i dobi te RAG dohvat s izvorima. Embedding pružatelj i MCP transport tek se implementiraju. Frontend zasad sadrži Vite/React početni prikaz.

## Struktura

Organizacija prati [FOIHireloom](https://github.com/imim77/FOIHireloom), pregledan na reviziji `8ba897db799e993aa43c7d488879efb3870218f2`:

```text
src/KIDSic/
  api/                      # budući MCP alati i app prikazi
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
  integrations/concrete/    # async httpx CKAN klijent i JSON dohvat
  services/interfaces/      # ugovori poslovnih operacija
  services/concrete/        # tumačenje upita i povezivanje pretrage s RAG-om
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

## Pokretanje

```sh
uv sync --locked
docker compose up -d --build --wait database
export DATABASE_URL=postgresql://kidsic:kidsic_local@127.0.0.1:55432/kidsic
uv run alembic -c src/KIDSic/db/alembic/alembic.ini upgrade head
uv run kidsic-register-sources
uv run kidsic-sync-kindergartens
uv run kidsic-search 'Imam dijete od 2 godine i iz varazdina sam koji su mi vrtici opcija'
```

Naredba pretražuje prethodno uvezene podatke. Bez imenika traži pojašnjenje jer grad nije poznat. Uvoz dodaje normalizirane gradske ključeve i poznate aliase za Zagreb, Varaždin, Rijeku, Split i Osijek. `.env.example` je predložak, a `.env` se ne učitava automatski. Postavke `DATABASE_POOL_MIN_SIZE` i `DATABASE_POOL_MAX_SIZE` upravljaju poolom. CLI trenutačno koristi leksički RAG dohvat; servis podržava i predani embedding s oznakom modela.

## CKAN registracija i uvoz

Obrazac je preuzet iz [FOIHireloom CKAN integracije](https://github.com/imim77/FOIHireloom/tree/8ba897db799e993aa43c7d488879efb3870218f2/src/FOIHireloom): caller-owned `httpx.AsyncClient`, interface i konkretni klijent, DTO validacija, odvojene HTTP/transport/API/response pogreške, servis, factory, Unit of Work i CLI s `--dry-run`. KIDSic koristi asyncpg za sve upise. MZOM-ov resurs ima tekstualni ID pa DTO prihvaća string umjesto isključivo UUID-a.

Početni izvori:

- `national`: [MZOM — Dječji vrtići](https://data.gov.hr/ckan/dataset/djecji-vrtici), osnovni nacionalni imenik.
- `zagreb-municipal`: [Gradski vrtići — kontakt podaci](https://data.zagreb.hr/dataset/gradski_vrtici_grada_zagreba), matični i područni objekti.
- `zagreb-other`: [Privatni/vjerski vrtići i obrti](https://data.zagreb.hr/dataset/privatni-vjerski-obrti-gz-kontakt-podaci), uz zasebno označene obrte dadilja.

```sh
# Bez DATABASE_URL i bez pristupa bazi:
uv run kidsic-register-sources --dry-run
uv run kidsic-sync-kindergartens --dry-run

# Odabir jednog ili više izvora; bez --source koriste se sva tri:
uv run kidsic-sync-kindergartens --source national
uv run kidsic-sync-kindergartens --source zagreb-municipal --source zagreb-other
```

Registracija poziva `package_show`, traži točno jedan aktivan JSON resurs i provjerava `open-license` (Otvorena dozvola). Metapodatke sprema u `data_source`; ponovljena registracija čuva `import_allowed`, aktivnu snimku i povijest. Ne uvozi sadržaj. Sync registrira izvore po potrebi i zasebno preuzima njihove JSON datoteke; ne pretpostavlja uključen DataStore. Nazivi portala, ID-jevi skupova, timeout i ograničenje veličine odgovora konfiguriraju se `CKAN_*` varijablama iz `.env.example`. Mapiranja su namijenjena ovim trima shemama.

Sync provjerava sve odabrane resurse prije transakcije. Sprema izvorne retke u `source_record`, normalizirane ustanove i objekte te podrijetlo polja. Spajanje koristi prethodni identitet izvora i normalizirane nazive, grad i adresu; ne koristi neprovjerene približne podudarnosti. Višeznačni zapisi ostaju `candidate` za pregled. Sve odabrane snimke aktiviraju se atomarno, a neuspjeh čuva prethodnu aktivnu snimku. Stari retci ostaju u povijesti. Ponovljeni uvoz istih identiteta čuva ID-jeve ustanova i lokacija; pisci se serijaliziraju transakcijskim advisory lockom.

Ovi skupovi nemaju potvrđene dobne uvjete, slobodna mjesta ni upisne upute. Uvoz ih ne izmišlja i ne stvara programe ni RAG dokumente iz kontaktnih podataka. Rezultati zato imaju dobni status `unknown`. Datum preuzimanja i izmjene resursa spremaju se odvojeno; ne proglašavaju se datumom stvarnog stanja podataka.

Frontend:

```sh
cd frontend
npm ci
npm run dev
```

Vite služi `src/views/index.html`; zajednički resursi su u `src/shared`. `npm run build` i `npm run lint` provjeravaju početni prikaz. MCP app HTML pakiranje još nije implementirano.

## Provjere i dokumentacija

```sh
uv run python -m unittest discover -s tests -v
```

Integracijske provjere trebaju zasebnu, migriranu bazu `kidsic_test_*` i `KIDSIC_TEST_DATABASE_URL`. Bez te varijable integracijski testovi se preskaču. Detalji: [baza i RAG](database/README.md), [ERA model](database/ERA.md), [funkcionalnosti](TO-DO.md).

Testovi CKAN klijenta i normalizacije rade offline. Testovi uvoza nad PostgreSQL-om provjeravaju ponovljivost, povijest, povezivanje izvora, nepoznatu dob i rollback. [Lokalna Postman simulacija](postman/README.md) dodatno provjerava stvarni HTTP promet, timeout i pogreške bez vanjskih servisa; uključuje se varijablom `KIDSIC_CKAN_SIMULATION_URL`.

Lokalno istraživanje u `docs/`, dokumentacija baze u `database/` i pomoćne skripte u `scripts/` ne ulaze u Git. Razvojni rezultati, `.env`, `.venv` i `node_modules` također su ignorirani. Commits slijede Conventional Commits (`chore`, `feat`, `test`, `docs` s odgovarajućim scopeom).
