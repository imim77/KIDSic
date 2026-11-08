# KIDSic

KIDSic je projekt za Datathon Portala otvorenih podataka 2026. Aplikacija koristi otvorene podatke za prikaz dječjih vrtića u Zagrebu, Varaždinu, Rijeci i Šibeniku.

## Preduvjeti

- Git i Make
- Docker s uključenim Docker Composeom
- Node.js 24 i npm
- [uv](https://docs.astral.sh/uv/getting-started/installation/) za Python. Projekt zahtijeva Python 3.14 ili noviji, koji `uv` može preuzeti.
- Internetska veza za instalaciju i kartu

Na Windowsu koristite WSL2.

## Lokalno pokretanje

Klonirajte repozitorij i pokrenite aplikaciju:

```sh
git clone https://github.com/imim77/KIDSic.git
cd KIDSic
make up
make start
```

Pri prvom `make up` PostgreSQL u novi Docker volumen automatski učitava snimku `snapshots/10-kidsic.sql.gz`. Ona sadrži strukturu i podatke naše baze, uključujući ručno pregledane lokacije, izvore, dokumente i stanje migracija. Za taj uvoz nije potreban pristup portalima otvorenih podataka. `make start` instalira ovisnosti, primjenjuje eventualne novije migracije i pokreće aplikaciju.

Snimka se učitava samo pri inicijalizaciji novog volumena. Postojeća baza ostaje sačuvana; promjena snimke u repozitoriju ne zamjenjuje lokalne podatke. Ako početni uvoz ne uspije, provjerite `docker compose logs database` prije nastavka; djelomično inicijaliziran volumen ne pokreće uvoz ponovno.

Otvorite [http://localhost:5173](http://localhost:5173) za pregled karte. MCP server dostupan je na `http://127.0.0.1:8001/mcp`.

Za zaustavljanje pritisnite `Ctrl+C` u terminalu u kojem radi aplikacija, a zatim pokrenite:

```sh
make stop
```

Podaci ostaju u Docker volumenu. Za ponovno pokretanje upotrijebite `make up` i `make start`.

## Ažuriranje snimke baze

Dok lokalna Compose baza radi, izvezite njezino trenutačno stanje:

```sh
make snapshot-db
```

Naredba koristi `pg_dump` iz kontejnera i atomarno zamjenjuje komprimiranu snimku tek nakon uspješnog izvoza. Izvozi Compose bazu `kidsic`, ne bazu iz varijable `DATABASE_URL`. Datoteku `snapshots/10-kidsic.sql.gz` uključite u sljedeći Git commit kako bi je dobili i drugi korisnici. Snimka ne sadrži PostgreSQL uloge ni njihove lozinke. Podaci zadržavaju licence i atribucije svojih izvora; prije dijeljenja nove snimke provjerite sadržaj koji ste dodali.

Za namjerno osvježavanje kataloga s portala ostaju dostupne naredbe `make register-sources` i `make sync-kindergartens`, te `make sync-historical` i `make sync-enrolment` za dodatne podatke.

Snimka PostgreSQL baze ne uključuje OTP grafove putovanja ni lokalne adresne indekse iz `routing/data/`. Za preporuke puta njih i dalje treba zasebno pripremiti i pokrenuti odgovarajuće servise iz `routing/compose.yaml`.

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

## Licenca

Izvorni programski kod ovog rješenja objavljen je pod licencom **Apache License 2.0**, koja dopušta besplatno korištenje, izmjenu i distribuciju, uključujući komercijalnu uporabu, uz poštovanje uvjeta licence.

Puni tekst licence dostupan je u datoteci [LICENSE](LICENSE). Vanjske programske komponente zadržavaju svoje izvorne licence, koje su zasebno navedene u dokumentaciji.
