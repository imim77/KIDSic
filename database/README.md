# KIDSic baza i RAG

[Model s 8 tablica](ERA.md) · [Dijagram](era.svg) · [Rječnik](rjecnik-podataka.md)

PostgreSQL 17 + pgvector + PostGIS. Aplikacija koristi asyncpg; Alembic koristi SQLAlchemy async engine samo za migracije.

## Pokretanje nove baze

```sh
uv sync --locked
docker compose up -d --build --wait database
export DATABASE_URL=postgresql://kidsic:kidsic_local@127.0.0.1:55432/kidsic
uv run alembic -c src/KIDSic/db/alembic/alembic.ini upgrade head
```

`.env.example` služi kao predložak; `.env` se ne učitava automatski. Compose koristi lokalne razvojne pristupne podatke i loopback port 55432. Dockerfile dodaje PostGIS službenoj pgvector slici; podržava i Apple Silicon.

Ovo zamjenjuje prethodni, neobjavljeni nacrt početne migracije. Nova revizija zove se `0001_simple_rag`. Ako je stari model već migriran u neku vašu bazu, **ne koristiti stamp ni reset nad tom bazom**: pokrenuti novu bazu/novi volume za ovaj model ili zasebno dogovoriti migraciju postojećih podataka. Postojeće baze ovim radom nisu promijenjene.

## Pretraga

```python
from KIDSic.config.settings import Settings
from KIDSic.services.dependency import DependencyService

async def example():
    dependencies = DependencyService(Settings.from_env())
    async with dependencies.kindergarten_search_service() as service:
        return await service.recommend(
            'Imam dijete od 2 godine i iz varazdina sam koji su mi vrtici opcija',
        )
```

Paket se instalira naredbom `uv sync --locked`; `PYTHONPATH` nije potreban. Kontekst `DependencyService` otvarati za životni vijek servisa. Svaki poziv koristi Unit of Work s read-only `repeatable_read` transakcijom, tako da kandidati i kontekst dolaze iz iste snimke.

Bez embeddinga radi leksički dohvat. Za semantički dohvat `recommend` prihvaća `embedding` (384 konačne vrijednosti, nenulti vektor) i `embedding_model`. Isti model mora prethodno indeksirati dokumente. Pružatelj/model nije ugrađen; nisu potrebni API ključevi za bazu i testove. Za proizvoljne upite MCP/LLM treba izdvojiti strukturirane filtre; mali parser pokriva navedeni primjer, uz popunjene gradske aliase.

## Provjere i dokumentacija

Na potrošnoj bazi `kidsic_test_*` s instaliranim ekstenzijama:

```sh
export KIDSIC_TEST_DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/kidsic_test_rag
DATABASE_URL="$KIDSIC_TEST_DATABASE_URL" uv run alembic -c src/KIDSic/db/alembic/alembic.ini upgrade head
uv run python -m unittest discover -s tests -v
DATABASE_URL="$KIDSIC_TEST_DATABASE_URL" uv run python scripts/export_database_model.py
dot -Tsvg database/era.dot -o database/era.svg
```

Bez testnog URL-a provjere se preskaču. Sintetički testovi provjeravaju korisnikov upit, dobne granice, nepoznate podatke, zastarjelost, filtriranje RAG-a, odvajanje modela, više skupova i očuvanje aktivne snimke. Ne dokazuju semantičku kvalitetu odabranog embedding modela na hrvatskom; to treba zasebno evaluirati na stvarnim upitima i podacima.

Migracije su eksplicitne (`target_metadata=None`, bez autogenerate). SQL uz reviziju je dio migracije. Buduće izmjene dobivaju novu reviziju. `uv run alembic -c src/KIDSic/db/alembic/alembic.ini downgrade base` briše aplikacijske tablice i podatke; provjeravati na potrošnoj bazi. Ekstenzije ostaju instalirane.
