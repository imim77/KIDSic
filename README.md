# KIDSic

KIDSic je projekt za Datathon Portala otvorenih podataka 2026. Aplikacija koristi otvorene podatke za prikaz dječjih vrtića u Zagrebu, Varaždinu, Rijeci i Šibeniku.

## Preduvjeti

- Git i Make
- Docker s uključenim Docker Composeom
- Node.js 24 i npm
- [uv](https://docs.astral.sh/uv/getting-started/installation/) za Python. Projekt zahtijeva Python 3.14 ili noviji, koji `uv` može preuzeti.
- Internetska veza za instalaciju, početni uvoz podataka i kartu

Na Windowsu koristite WSL2.

## Lokalno pokretanje

Klonirajte repozitorij i pokrenite aplikaciju:

```sh
git clone https://github.com/imim77/KIDSic.git
cd KIDSic
make up
make start
```

Pri prvom pokretanju Makefile instalira ovisnosti, priprema bazu i uvozi podatke s otvorenih portala. Uvoz ovisi o dostupnosti tih portala. Repozitorij ne sadrži potpunu snimku naše lokalne baze, pa neke ručno pregledane lokacije neće biti dostupne.

Otvorite [http://localhost:5173](http://localhost:5173) za pregled karte. MCP server dostupan je na `http://127.0.0.1:8001/mcp`.

Za zaustavljanje pritisnite `Ctrl+C` u terminalu u kojem radi aplikacija, a zatim pokrenite:

```sh
make stop
```

Podaci ostaju u Docker volumenu. Za ponovno pokretanje upotrijebite `make up` i `make start`.

## Povezivanje s AI klijentom

KIDSic možete povezati s ChatGPT-om, Claudeom ili drugim MCP klijentom. Za interaktivnu kartu klijent treba podržavati MCP Apps.

ChatGPT i Claudeovi udaljeni konektori ne mogu pristupiti adresi `127.0.0.1` na vašem računalu. Za povezivanje upotrijebite HTTPS tunel ili postavite server na dostupnu HTTPS adresu i unesite adresu koja završava s `/mcp`.

- [Povezivanje s ChatGPT-om](https://developers.openai.com/plugins/build/app-quickstart)
- [Povezivanje s Claudeom](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp)

KIDSic nema ugrađenu autentikaciju za javni endpoint. Prije javnog izlaganja potrebno je zaštititi pristup serveru.

Nakon povezivanja pokušajte: "Prikaži mi vrtiće u Zagrebu na karti."

## Testovi

```sh
make test
make test-frontend
```

Integracijski testovi baze zahtijevaju zasebnu migriranu PostgreSQL bazu naziva `kidsic_test_*` i varijablu `KIDSIC_TEST_DATABASE_URL`. Bez nje se preskaču.
