# KIDSic

MCP app u razvoju za pronalazak dječjih vrtića povezivanjem više otvorenih skupova. Trenutačno su implementirani PostgreSQL model, SQL pretraga prema gradu i dobi te RAG dohvat s izvorima. Uvoznici stvarnih podataka, embedding pružatelj i MCP transport tek se implementiraju. Frontend zasad sadrži Vite/React početni prikaz.

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
    models/                 # rezervirano; nema ORM-a u trenutačnoj izvedbi
    uow/                    # transakcije i životni vijek konekcije
  dto/                      # podatkovni ugovori i normalizacija teksta
  factories/                # sastavljanje servisa iz ovisnosti
  integrations/interfaces/  # budući ugovori vanjskih izvora
  integrations/concrete/    # budući klijenti otvorenih podataka
  services/interfaces/      # ugovori poslovnih operacija
  services/concrete/        # tumačenje upita i povezivanje pretrage s RAG-om
  services/dependency.py    # životni vijek infrastrukture
  main.py                   # ulazna točka
frontend/src/
  shared/                   # zajednički stilovi i resursi
  views/                    # HTML ulazi i React prikazi
scripts/                    # pomoćni razvojni alati
tests/                      # provjere servisa, infrastrukture i upita
database/                   # ERA model, generirani rječnik i Dockerfile
```

Tok ovisnosti: naredba/API → DependencyService/factory → service → Unit of Work → DAO interface → asyncpg DAO. SQL i vektorski operatori pripadaju konkretnom DAO-u; servis odlučuje koje kandidate i dokaze vratiti. Transakcije pripadaju Unit of Worku. Struktura prati referentni projekt uz traženi izravni asyncpg pristup; SQLAlchemy se koristi samo za Alembic.

## Pokretanje

```sh
uv sync --locked
docker compose up -d --build --wait database
export DATABASE_URL=postgresql://kidsic:kidsic_local@127.0.0.1:55432/kidsic
uv run alembic -c src/KIDSic/db/alembic/alembic.ini upgrade head
uv run kidsic-search 'Imam dijete od 2 godine i iz varazdina sam koji su mi vrtici opcija'
```

Naredba zahtijeva prethodno uvezene podatke i gradske aliase; bez njih traži pojašnjenje jer grad ne postoji u imeniku. `.env.example` je predložak, a `.env` se ne učitava automatski. Postavke `DATABASE_POOL_MIN_SIZE` i `DATABASE_POOL_MAX_SIZE` upravljaju poolom. CLI trenutačno koristi leksički RAG dohvat; servis podržava i predani embedding s oznakom modela.

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

Lokalno istraživanje ostaje u ignoriranom `docs/`. Razvojni rezultati, `.env`, `.venv` i `node_modules` ne ulaze u Git. Commits slijede Conventional Commits (`chore`, `feat`, `test`, `docs` s odgovarajućim scopeom).
