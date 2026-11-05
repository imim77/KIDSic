# Vrtić koji se uklapa u moj dan — stvarni podaci za Rijeku

MCP alat `preporuci_vrtice_usput` uspoređuje dom → vrtić → posao preko lokalnog
OpenTripPlannera 2.8.1. Koristi stvarne objekte iz postojeće baze, pješačku OSM
mrežu i GTFS vozni red. Nema oglednih vrtića, unaprijed upisanih rezultata ni
zamjene stvarnog izračuna sintetičkim podacima. Bez baze ili rutera prikazuje grešku.

## Izvori i verzije

- GTFS: [vekejsn / gtfs-generators](https://gitlab.com/vekejsn/gtfs-generators),
  objavio Nedžad Beus. README navodi da je riječki feed generiran iz gradskih
  otvorenih CSV podataka na https://e-usluge2.rijeka.hr/OpenData/.
- [Transitous registry](https://transitous.org/sources/#croatia) za taj feed
  navodi **CC-BY-4.0** i atribuciju OpenStreetMap contributors. To je verzija
  zajednice generirana iz stvarnih podataka; nije izvorni Autotrolej GTFS ZIP.
- Preuzeto 5. 11. 2026.; SHA256
  `e2d9357c5f020d6d4081ba114509d89f51a33dd224d09aae09ff6c1e4c0849bd`.
  Feed navodi valjanost **9. 10. – 8. 11. 2026.**, 1.187 stajališta, 59 linija,
  3.988 putovanja i 78.163 zapisa vremena stajanja.
- OSM: [Geofabrik Hrvatska](https://download.geofabrik.de/europe/croatia.html),
  snapshot `2026-11-04T21:21:03Z`, **ODbL-1.0**, © OpenStreetMap contributors.
  Izrezano područje `[14.20, 45.20, 14.65, 45.45]` (zapad, jug, istok, sjever).
  Zadržane su cjelovite prometnice i ograničenja skretanja, 36.640 highway objekata.
- Koordinate i adrese vrtića dolaze iz postojećeg `/api/locations?city=Rijeka`,
  koji vraća izvore i licence. Uspoređuju se samo mapirani objekti s adresom.
- Leaflet: BSD-2-Clause; OpenTripPlanner: LGPL-3.0.

[manifest.json](manifest.json) bilježi hash izrezanog OSM-a, izvore, verziju i
poznate probleme pri uvozu. Arhive, JAR i graf ostaju lokalni i nisu u Gitu.
Ranije razmatrana Transitland snimka 25475e41… više se ne koristi. Nisu potrebni
Google, Mapbox ni Transitland ključevi za ovaj izračun.

## Preuzimanje i izgradnja

Iz korijena projekta, uz instaliran `uv` i Java runtime ili Docker:

```sh
uv run python routing/download_gtfs.py
mkdir -p routing/cache
curl -fL https://download.geofabrik.de/europe/croatia-latest.osm.pbf \
  -o routing/cache/croatia.osm.pbf
uv run --with osmium==4.3.2 python routing/extract_osm.py \
  routing/cache/croatia.osm.pbf routing/data/rijeka.osm.pbf
uv run python routing/prepare.py --gtfs routing/data/autotrolej-gtfs.zip \
  --osm routing/data/rijeka.osm.pbf \
  --osm-source https://download.geofabrik.de/europe/croatia.html
```

GTFS URL sadrži `latest`; skripta odbija drukčiji SHA256. Ako izdavač promijeni
ZIP, novu verziju i njezin kalendar treba pregledati prije ažuriranja pina i
vremenskih granica u `dto/day_route.py`, konfiguraciji grafa i sučelju.
Geofabrik `latest` također se mijenja: hash svakog pripremljenog OSM-a zapisuje
se u `routing/data/provenance.json`; za identičan graf zadrži preuzete datoteke.
`routing/cache` mora biti izvan `routing/data`, kako OTP ne bi učitao cijelu
Hrvatsku umjesto riječkog isječka.

Docker:

```sh
docker compose -f routing/compose.yaml run --rm otp --build --save
docker compose -f routing/compose.yaml up -d
```

Ili Java (provjereno s OpenJDK 26.0.1):

```sh
curl -fL https://repo.maven.apache.org/maven2/org/opentripplanner/otp-shaded/2.8.1/otp-shaded-2.8.1.jar \
  -o routing/data/otp.jar
java -Xmx3G -jar routing/data/otp.jar --build --save routing/data
java -Xmx3G -jar routing/data/otp.jar --load --serve \
  --bindAddress 127.0.0.1 --port 18080 routing/data
```

Ponovi izgradnju nakon promjene podataka ili konfiguracije. Nemoj pokrenuti
i Docker i Java ruter na istom portu. Ruter je dostupan samo lokalno.

## Aplikacija

Postojeća razvojna baza mora biti pokrenuta i sadržavati riječke objekte.
Postavi DATABASE_URL u `.env`, kao u `.env.example`. Opcionalni `OTP_URL`
ima zadanu vrijednost `http://127.0.0.1:18080/otp/gtfs/v1`.
Pripremi adresni indeks prema uputama na kraju dokumenta, zatim:

```sh
npm --prefix frontend run build:mcp
uv run uvicorn KIDSic.api.mcp_server:create_app --factory --env-file .env \
  --host 127.0.0.1 --port 8002
```

Poveži ChatGPT/MCP klijent s `/mcp` prema [MCP.md](../MCP.md).
Korisnik u razgovoru navodi dom, posao, datum i vrijeme polaska te način prijevoza.
Sustav sam uspoređuje sve mapirane objekte; nema zasebne demo stranice ni ručnog
predodabira vrtića. Koordinate se koriste lokalno i ne spremaju se.
OSM pločice dolaze s `tile.openstreetmap.org`; prikazana je atribucija i nema
preuzimanja pločica unaprijed.

## Izračun i granice

Prvi put vodi do vrtića. Drugi počinje nakon dolaska i zadanog trajanja predaje.
Ukupno vrijeme uključuje čekanje od zadanog polaska. Rangira se prema
najranijem dolasku među OTP-ovim vraćenim alternativama, a dodatne minute
uspoređuju se s izravnim putem za isti polazak. U načinu javnog prijevoza OTP
smije vratiti samo hodanje ako je to bolje. Presjedanja se broje unutar svakog
dijela puta; predaja djeteta nije presjedanje. Karta prikazuje geometriju
najbolje vraćene opcije; odabir druge kartice prikazuje njezinu rutu na istoj
sivoj karti kao opća pretraga. `top_k` određuje ukupan broj vraćenih vrtića
(pozitivan cijeli broj, zadano 4), nakon rangiranja cijelog mapiranog kataloga.

- Podaci su raspored polazaka, bez kašnjenja i vozila uživo. Izračunata vremena
  nisu jamstvo stvarnog dolaska ni dostupnosti mjesta u vrtiću.
- Radno vrijeme objekata nije potvrđeno u bazi i ne utječe na rang.
- Cijeli GTFS sadrži i prigradske linije, dok je ulična mreža ograničena na
  navedeni okvir Rijeke. Rubna stajališta mogu ostati nepovezana s ulicama.
- OTP je pri uvozu prijavio 69 izoliranih stajališta, 76 stajališta nepovezanih
  za presjedanja, 28 degeneriranih putovanja i jedan negativni interval između
  stajališta. Dio se odnosi na izrez mreže, dio na izvorni feed. Uvoz i uspješan
  primjer ne potvrđuju kvalitetu svih putovanja. Izvorne arhive nisu ručno mijenjane.
- OTP `plan` je kompatibilan s prikvačenom verzijom, ali deprecated u novijim
  izdanjima; nadogradnja traži provjeru adaptera ili migraciju na `planConnection`.

## Provjera

```sh
uv run python -m unittest discover -s tests
cd frontend
npm test
npm run build
npm run lint
```

Automatski testovi koriste sintetičke odgovore samo kao testne fixture.
Stvarna MCP integracija provjerena je 5. 11. 2026. za adrese Zametska 6 i
Korzo 16, polazak u 07:00, javni prijevoz i predaju djeteta od 10 minuta.
Uspoređeno je 27 mapiranih objekata, a vraćeni su Mala vila (31 minuta),
Gardelin (39), Val (42) i Mima (43). Rezultati se računaju iz podataka, nisu
upisani u aplikaciju. Promjena adresa, datuma ili prijevoza ponavlja izračun.

## Razgovorni odabir najbolje opcije i tri alternative

MCP alat `preporuci_vrtice_usput` prima adrese doma/posla ili izričite koordinate
i uspoređuje sve mapirane objekte. Za lokalno razrješavanje adresa izgraditi indeks:

```sh
uv run --with osmium==4.3.2 python routing/index_addresses.py \
  routing/cache/croatia.osm.pbf routing/data/addresses.sqlite
```

Indeks dolazi iz istog OSM snapshota, pod ODbL licencom. Potpuni razgovorni ugovor,
pojašnjenja nejasnih adresa i MCP prikaz opisani su u [MCP.md](../MCP.md).
