# Testovi

Backend koristi standardni `unittest`, a frontend Vitest i Testing Library.

```sh
.venv/bin/python -m unittest discover -s tests
npm --prefix frontend test
npm --prefix frontend run test:typecheck
npm --prefix frontend run lint
```

Integracijski testovi zahtijevaju migriranu bazu `kidsic_test_*` kroz
`KIDSIC_TEST_DATABASE_URL`. Bez nje se preskaču. Testovi stvarnog CKAN HTTP
prijenosa dodatno zahtijevaju `KIDSIC_CKAN_SIMULATION_URL`; lokalni HTTP testovi
koriste `httpx.MockTransport` i ne pristupaju javnim izvorima.

## Organizacija i održavanje

- `support/` sadrži zajedničke fixturee, konstrukciju servisa i MCP sesije.
  Testne datoteke ne uvoze druge testne datoteke.
- `DatabaseTestCase` otvara konekciju i rollback transakciju za svaki test.
  Podklase pozivaju `await super().asyncSetUp()` prije vlastite pripreme.
  Čišćenje resursa registrirano je odmah, pa radi i ako priprema zakaže.
- `frontend/test-support/` sadrži sintetičke podatke i zajedničku pripremu DOM-a.
  `setup.ts` uklanja komponente, vraća globalne objekte i scroll metode.
  Posebne mockove i promjene drugih prototipova čisti test koji ih uvodi.
- Jedan test opisuje jedno ponašanje. Za varijante istog pravila koriste se
  `subTest` ili `it.each`, s podacima koji jasno identificiraju pogrešku.
- Svaki test priprema vlastite promjenjive podatke. Asinkroni callbackovi vežu
  vrijednosti svojeg scenarija; mockovi ne smiju nasljeđivati rezultate ranijeg
  testa. Provjere koje ovise o vremenu koriste kontrolirani sat.
- Zadržavaju se provjere javnog ugovora, poslovnih pravila, migracija, podrijetla
  podataka i sigurnosnih granica. Duplikati se spajaju uz očuvanje jedinstvenih
  asercija; uklonjeni parametri trebaju provjeru odbijanja, a ne stare provjere
  svih njihovih vrijednosti.

Testovi migracija `0004`, `0005` i `0013` u `test_source_database.py`
rekonstruiraju dijelove stare sheme uz trenutačne SQL nazive. Čuvaju provjere
prijenosa podataka, uključujući uklonjene tablice i stupce; ne potvrđuju da su
stare funkcionalnosti još dostupne niti zamjenjuju provjeru cijele Alembic
migracijske putanje.

Neovisnost frontend testova može se provjeriti promjenom redoslijeda:

```sh
npm --prefix frontend test -- --sequence.shuffle --sequence.seed=20261107
```
