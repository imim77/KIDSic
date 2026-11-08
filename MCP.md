# KIDSic MCP app

`prikazi_vrtice` je read-only MCP alat koji vraća postojeći GeoJSON za grad i
prikazuje kartu s vodoravnim karticama. Filtrira grad, naziv, vrstu pružatelja,
područje i radijus; ne potvrđuje dobnu prikladnost, pravo na upis ni slobodna mjesta.

## Pokretanje

Najprije pripremiti migriranu i uvezenu bazu prema [README-u](README.md).
Iz korijena repozitorija:

```sh
uv sync --locked
npm --prefix frontend ci
npm --prefix frontend run build:mcp
export DATABASE_URL=postgresql://kidsic:kidsic_local@localhost:55432/kidsic
uv run uvicorn KIDSic.api.mcp_server:create_app --factory --host 127.0.0.1 --port 8001
```

`KIDSic.mcp.server:create_app` ostaje kompatibilni ulaz za postojeće postavke.
Transport je u `api/mcp_server.py`, grupa alata u `api/location_tools.py`,
a HTML resurs u `api/apps/map_resource.py`.

Streamable HTTP endpoint je `http://127.0.0.1:8001/mcp`. Server pri pokretanju
učitava `frontend/dist/mcp.html` i otvara jedan pool baze. Ako build nedostaje,
pokretanje završava jasnom porukom. Nakon promjene builda ponovno pokrenuti
server. Pakiranje Python wheela samo ne uključuje frontend; deployment mora
isporučiti taj HTML. Ne pokreću se migracije niti uvoz pri startu.

`npm run build` čisti frontend `dist`; ako se gradi i samostalni preview, zatim
pokrenuti `build:mcp`. Karta koristi Leaflet i OpenStreetMap bez API tokena.

## Spajanje AI klijenta

Klijent mora podržavati MCP Apps, a ne samo tekstualne MCP alate. Lokalni klijent
s pristupom istom računalu može koristiti gornji HTTP endpoint. ChatGPT treba
server dostupan svojem okruženju, primjerice kroz podržani razvojni tunel ili
HTTPS deployment; `127.0.0.1` na računalu nije javni endpoint. Registracija u
ChatGPT-u i javna objava nisu dio lokalnog pokretanja. Za javni deployment
primijeniti autentikaciju/pristup i operativna ograničenja svojeg hostinga.

Nakon povezivanja odabrati KIDSic aplikaciju u chatu i pokušati:

- „Prikaži mi vrtiće u Zagrebu na karti.” → alat s `{"city":"Zagreb"}` i mapa.
- „Prikaži mi vrtiće u Rijeci.” → isti pogled s rezultatima Rijeke.
- „Prikaži vrtić Bajka u Zagrebu.” → `{"city":"Zagreb","name":"Bajka"}`.
- „Samo gradski vrtići u Zagrebu.” → `{"city":"Zagreb","provider_kind":"municipal"}`.
- „Privatni vrtić Bajka u Varaždinu.” → `{"city":"Varaždin","name":"Bajka","provider_kind":"private"}`.
- „Vrtići na Banfici u Varaždinu.” → `{"city":"Varaždin","area":"Banfica"}`.
- „Tražim Čarobnu kućicu.” → pitati za grad, bez pretrage po pretpostavljenom gradu.
- „Prikaži mi vrtiće u Splitu.” → poruka da su podržani Zagreb, Varaždin, Rijeka i Šibenik, bez čitanja baze.
- „Prikaži mi vrtiće.” → AI pita „U kojem gradu želiš prikaz vrtića?” prije poziva.
- „Gradski vrtići u Zagrebu u krugu 1 km od mene.” → `{"city":"Zagreb","provider_kind":"municipal"}`
  i molba da korisnik odabere točku na karti (gumb „Odaberi na karti” ili „Moja lokacija”);
  AI ne procjenjuje koordinate iz adrese.
- Točka odabrana na karti → app sam poziva alat s istim kriterijima i
  `"near":[dužina,širina],"radius_m":1000`, a modelu kroz `updateModelContext`
  javlja točku i radijus kako bi ih zadržao u sljedećem pozivu.

Opcionalni `near` (`[dužina, širina]` u WGS84) i `radius_m` (cijeli metri,
1–50000) šalju se zajedno i ograničavaju rezultate na zračni radijus, kao
`GET /api/locations` ([LOCATION_API.md](LOCATION_API.md)). Objekti bez potvrđenih
koordinata nisu uključeni, a svaki rezultat nosi `distance_m`. Rezultati su
poredani od najbližeg (nakon potvrđene prikladnosti), a app iznad kartica
navodi broj rezultata, aktivne kriterije i redoslijed. Udaljenost nije
vrijeme putovanja. Model koristi samo koordinate iz karte ili brojeve koje je
korisnik izričito naveo. „Moja lokacija” ovisi o tome dopušta li sandbox hosta
geolokaciju; ako ne, kontrola upućuje na odabir na karti.

Grad je obavezan string od 1 do 100 znakova nakon trimanja, bez defaulta. Poziv
bez grada, s praznim/nepodržanim gradom ili nepoznatim argumentima vraća `isError` i uputu za
pojašnjenje bez čitanja baze. Alat ne zaključuje grad iz geolokacije. Klijent treba
iz razgovornog oblika („u Zagrebu”) predati naziv grada („Zagreb”).

Opcionalni `name` je naziv ili dio naziva ustanove/objekta (najviše 200 znakova),
bez cijele rečenice upita. Izostavljen ili prazan naziv vraća sve objekte grada.
Podržane padežne oblike grada server pretvara u kanonski naziv. Pretraga je
literalno podudaranje dijela naziva, bez razlikovanja veličine slova i hrvatskih
slova č/ć/ž/š/đ. `%` i `_` nisu zamjenski znakovi. Ne pretražuju se opisi ni adrese.

Opcionalni `provider_kind` ograničava rezultate na jednu vrstu ustanove:
`municipal` (javni/gradski), `private` (privatni), `religious` (vjerski),
`childminder` (obrt dadilja), `other` (drugi pružatelj), `unknown` (nepoznata vrsta).
AI klijent prevodi korisnikov izraz u ove vrijednosti. Izostavljeno ili `null`
znači sve vrste, uključujući ostale i nepoznate; prazan string nije valjan filter.
Više vrsta u jednom pozivu nije podržano: prvo razjasniti koju korisnik želi,
a ne prešutno odabrati samo jednu. Vrsta se kombinira s gradom i nazivom logikom
AND, bez promjene razvrstavanja podataka ili boja oznaka na karti.

Opcionalni `area` je jedan naziv četvrti, predjela ili naselja (triman, najviše
200 znakova). Izostavljeno ili `""` znači sva područja; `null` i popis nisu
podržani. Podudaranje je točno, bez razlikovanja velikih slova i hrvatskih
dijakritika; prefiks `Mjesni odbor ` je opcionalan, pa `Zamet` podudara
`Mjesni odbor Zamet`. AI klijent pretvara padež u nominativ, npr. „na Banfici”
u `Banfica`. Ne pretražuju se naziv ni adresa vrtića kao zamjena za područje.
Filter koristi aktualne zapise područja, uključujući geokodirana sjedišta s
važećim dokazom i nepromijenjenom adresom. Nepoznato područje se ne pretpostavlja.
OSM nazivi ne potvrđuju službene granice; pokrivenost je nepotpuna i nula
rezultata ne dokazuje da u području nema vrtića.

Dobni/programski filtri i aktualni programi uklonjeni su u migraciji 0012.
Parametri `age_months`, `program` i `include_unknown` odbijaju se; alat ne
prikazuje oznake prikladnosti ni brojeve potvrđenih/nepoznatih uvjeta.
Za pitanje o programu imenovane ustanove alat `dohvati_kontekst_vrtica` može
vratiti povijesno objavljene programe, uz datum i upozorenje da ne potvrđuju
aktualnu provedbu. Program se ne smije prešutno pretvoriti u naziv ustanove.

Detalji zagrebačkih vrtića dodatno prikazuju `historical_data`: programe iz XLSX-a
objavljenog 9. 10. 2019. i slobodna mjesta iz CSV snimki na dan 1. 1. 2025.
Prikazuju datum, opseg objekt/ustanova, izvor i licencu. Institucionalni broj
mjesta nije broj za svaki objekt i ne smije se zbrajati po podružnicama.
Povijesne snimke ne ulaze u potvrdu današnje dobi/programa ni slobodnih mjesta.
Uvoz i povezivanje dokumentirani su uz `kidsic-sync-historical` u README-u.

Odjeljak „Upis” prikazuje `enrolment`: pedagošku godinu, status roka prema
trenutnom vremenu, kanal, izvor i licencu. Gumb „Otvori službeni upis” postoji
samo za otvoren ili budući krug, ide kroz host (`openLink`) i označava da vodi
na vanjsku uslugu; KIDSic ne predaje zahtjev. Bez potvrđenog kanala prikazuje
se uputa da se upis provjeri kod vrtića. Format: [LOCATION_API.md](LOCATION_API.md#upis-u-detaljima).

Svaki poziv sadrži sve odabrane kriterije. Na nastavak „A sada samo u Centru”
klijent zadržava prethodno izričito utvrđen grad, naziv i vrstu ako ih korisnik
želi zadržati, a šalje `area: "Centar"`. Na „Ukloni područje” izostavlja `area`
ili šalje `""`. Server ne čuva razgovorno stanje. Ako grad ili željena promjena
nisu jasni, klijent traži pojašnjenje. Promjena kriterija prikazuje novi skup
rezultata i briše stari odabir kartice.

Uspješan rezultat uvijek vraća primijenjeni `city`, `name`, `provider_kind`, `area`, `near` i `radius_m`. UI čuva kriterije
pri ponovnom pokušaju i briše prethodni odabir pri novom upitu, bez gornjeg reda
filtra iznad karte. Nula rezultata prikazuje praznu kartu s pozivom da se naziv provjeri ili
skrati; server i UI ne proširuju pretragu automatski. Za sve vrste izostaviti `provider_kind` ili poslati `null`; za sve nazive
izostaviti `name`. Novi poziv bez vrste ili područja ne nasljeđuje te filtre prethodne pretrage.

Tumačenje prirodnog jezika i pitanje za nedostajući grad obavlja AI klijent
prema opisu alata i uputama servera. Python server validira strukturirane
argumente i izvršava determinističku pretragu; nema zasebnog LLM poziva ni
novog chat polja u web aplikaciji. RAG kontekst dostupan je kroz zaseban alat
`dohvati_kontekst_vrtica`; usporedba i vodič za upis još nisu implementirani.

Odabir oznake na karti, kartice ili retka popisa šalje modelu preko
`updateModelContext` točan `feature_id`, ID ustanove, grad, naziv ustanove i
objekta, adresu te opseg objekt/sjedište. Isto vrijedi za odabir i navigaciju
među rutama. Na pitanje poput „Koje dokumente trebam za ovaj vrtić?” model
koristi `city`, `name` i `feature_id` odabranog objekta za RAG dohvat.
Zatvaranje detalja, nova pretraga ili rezultat te prekid alata uklanjaju
prethodni odabir iz konteksta. Odabir ne mijenja kriterije ni rang rezultata
i ne potvrđuje činjenice o vrtiću; izvorni nazivi i adrese ostaju podaci.

### RAG odgovori o odabranom vrtiću

`dohvati_kontekst_vrtica` prihvaća obavezne `city` i `name` te neobavezne `topics`
(teme pitanja koje bira model klijenta) i `feature_id` iz prethodnog rezultata. Vraća tekstualne i strukturirane dokaze s
izvorima, datumima i opsegom bez metapodataka karte. Model klijenta na temelju
njih sastavlja odgovor i citira izvore. Višeznačan naziv traži odabir; odsutnost
dokaza nije dokaz da usluga ne postoji. Povijesna snimka nikada ne potvrđuje
današnje programe ili slobodna mjesta. Detaljan ugovor i ograničenja: [RAG.md](RAG.md).

Server ne rangira dokaze niti tumači pitanje. Vraća sve prihvaćene dokaze
odabranih tema za odabranu ustanovu/objekt jer oni stanu u ograničenje odgovora;
namjeru pitanja određuje model klijenta kroz `topics`.

Upute servera i opis alata zahtijevaju ovaj alat za prikaz vrtića. Svaki poziv je
povezan s UI resursom u definiciji alata i metapodacima rezultata. Server ipak ne
može prisiliti proizvoljan AI klijent da pozove alat ili renderira MCP Apps;
te dvije stvari treba potvrditi u ciljnom klijentu. Tekstualni MCP klijent može
pročitati rezultat, ali ne može prikazati interaktivnu kartu.

## Ugovor UI-ja i provjera

Resurs `ui://kidsic/map-v35.html` ima MIME `text/html;profile=mcp-app`. Hostovi
predložak spremaju po URI-ju, pa se verzija u URI-ju podiže pri svakoj promjeni
UI-ja, a server se nakon `build:mcp` mora ponovno pokrenuti. Moderni
`_meta.ui.resourceUri` i kompatibilni `openai/outputTemplate` povezuju ga s alatom.
Uspješan rezultat ima sažetak `structuredContent: {city, name, provider_kind, area, near, radius_m, metadata}`, uz deklarirani
`outputSchema`. Potpuni GeoJSON prenosi se bez gubitka u `_meta.locations` kao
`{encoding: "gzip+base64", data: "…"}`. UI ga dekodira preko pregledničkog
`DecompressionStream` API-ja prije validacije. Time veliki gradski skupovi s
ponovljenim izvorima ostaju unutar hostovih ograničenja veličine odgovora;
vrtići, koordinate i podrijetlo polja ne izostavljaju se. Host prosljeđuje te
metapodatke UI-ju bez unošenja svih izvora u kontekst modela. Prazan skup i dalje
vraća kartu s porukom, a zapisi bez koordinata ostaju u karticama. Trenutni
izvori imaju potvrđene koordinate uglavnom za Zagreb; drugi gradovi mogu imati
samo sjedišta na popisu. Kvar baze vraća sanitiziranu pogrešku, nikad lažni prazan
uspješan rezultat.

UI koristi službeni `App` bridge, `ui/notifications/tool-input` i `tool-result`,
čisti stare kartice pri novom gradu te traži `ui/request-display-mode` od hosta
koji podržava fullscreen. Bez te mogućnosti ostaje postojeći browser fallback.
Inline prikaz ima vlastitu visinu 520 px (480 px na uskim ekranima), koju SDK
prijavljuje hostu kroz automatski `size-changed`. Ne preuzima malu početnu
visinu iframea kroz `100dvh`. MCP kartice visoke su 92 px (144 px s oznakom potvrđenog podudaranja); fullscreen koristi
visinu dodijeljenog prozora. Klik na karticu traži fullscreen i otvara popis,
detalje i kartu u stupcima (ispod 1100 px detalji prekrivaju popis, ispod 700 px
kartu). Detalji prikazuju samo podatke iz izvora i navode što nije poznato;
vanjske poveznice otvaraju se kroz `ui/open-link`. Nakon nadogradnje ponovno
povezati konektor kako bi host preuzeo URI resursa v32 te pokrenuti novi poziv
alata.
Resurs deklarira CSP za `https://tile.openstreetmap.org` i ugrađene data resurse.
Leaflet ne zahtijeva WebGL ili Web Workere. UI je jedan HTML bez relativnih
JS/CSS zahtjeva. URI resursa je v23; nakon nadogradnje ponovno povezati
konektor i pozvati alat kako bi host preuzeo novu verziju.

### MCP Inspector: kartice su vidljive, karta je prazna

Provjeriti dopušta li CSP hosta slike s `https://tile.openstreetmap.org` i
ima li preglednik internetsku vezu. Ograničenje `worker-src 'none'` ne ometa
Leaflet. Kartice i odabir lokacija ostaju dostupni ako se podloga ne učita.
Pločice koriste standardno pregledničko predmemoriranje, bez preuzimanja unaprijed.
Atribucija je stalno vidljiva prema
[pravilima OpenStreetMap pločica](https://operations.osmfoundation.org/policies/tiles/).

```sh
uv run python -m unittest discover -s tests -v
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
npm --prefix frontend run build:mcp
```

MCP testovi koriste službeni Python `ClientSession` preko stvarnog ASGI HTTP
transporta, bez baze. Frontend provjerava i stvarni SDK `postMessage` handshake,
primanje rezultata i host fullscreen uz simulirani host. To ne zamjenjuje konačnu
provjeru u ChatGPT-u: povezati server, isprobati podržane gradove i upit bez grada,
potvrditi podlogu, odabir kartica i izlazak iz fullscreena.

Reference: [MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview),
[UI povezivanje u ChatGPT-u](https://developers.openai.com/plugins/build/chatgpt-ui).

Scenariji za provjeru filtra područja i nastavaka razgovora nalaze se u
[conversational_area.md](tests/fixtures/conversational_area.md).

Scenariji za dob i programe: [conversational_age_program.md](tests/fixtures/conversational_age_program.md).

## Vrtić na putu od doma do posla (Rijeka, Zagreb i Šibenik)

`preporuci_vrtice_usput` je alat za razgovorni upit poput:

> Živim na Zametskoj 6 u Rijeci, radim na Korzu 16. Krećem od doma
> 5. studenoga 2026. u 07:00 i koristim javni prijevoz. Koji su mi vrtići
> najbolja opcija na putu do posla?

ChatGPT iz razgovora izdvoji `city`, `home`, `work`, `departure` i `mode`.
Ako datum, lokacija ili način putovanja nisu jasni, prvo postavi pitanje.
Samo „ujutro u 7” ne određuje dan voznog reda. Vrijeme bez offseta računa se
u Europe/Zagreb. Predaja djeteta zadano je 10 minuta i mora se navesti u odgovoru;
roditelj je može promijeniti kroz razgovor (`dropoff_minutes`, 0–60).

Primjer poziva:

```json
{
  "city": "Rijeka",
  "home": "Zametska 6",
  "work": "Korzo 16",
  "departure": "2026-11-05T07:00",
  "mode": "TRANSIT",
  "dropoff_minutes": 10,
  "top_k": 4
}
```

Za Zagreb isti alat prima `city="Zagreb"`, primjerice `home="Ilica 10"`,
`work="Radnička cesta 1"`, `departure="2026-11-06T07:00"`, `mode="TRANSIT"`.
Pretražuje se zagrebački katalog; adrese i prometni graf odvojeni su po gradu.
Prikvačeni ZET raspored pokriva 21. 10. – 31. 12. 2026.; riječki ostaje
9. 10. – 8. 11. 2026. Alat odbija koordinate drugog grada i datume izvan
rasporeda odabranog grada. Postupak pripreme Zagreba je u [routing/README.md](routing/README.md#zagreb).

Adrese se razrješavaju u lokalnom OSM indeksu; ne šalju se vanjskom geokoderu.
Za indeks treba izvorni Geofabrik PBF, jer mali cestovni isječak ne sadrži
sve kućne brojeve i zgrade. Nakon pripreme [rutera](routing/README.md) pokrenuti:

```sh
uv run --with osmium==4.3.2 python routing/index_addresses.py \
  routing/cache/croatia.osm.pbf routing/data/addresses.sqlite
npm --prefix frontend run build:mcp
```

Riječki indeks je fiksno `routing/data/addresses.sqlite`, a zagrebački
`routing/data/zagreb/addresses.sqlite`. Postojeći
snapshot daje 8.831 adresni ili imenovani POI zapis u obuhvatu Rijeke i okolice.
Zapisi s izričitim `addr:city` izvan Rijeke isključeni su; zapisi bez grada
ograničeni su geografskim okvirom. Zato model treba tražiti grad i točnu adresu,
a korisnik treba provjeriti da izabrani položaj odgovara namjeri. Koordinate
zgrada računaju se iz njihove geometrije; nisu potvrda ulaza u objekt.
Nema fuzzy geokodiranja: samo jedinstven točan normalizirani naziv/adresa
razrješava se automatski. Nepotpuni ili višeznačni upit vraća
`status=clarification_required` s kandidatima; roditelj treba potvrditi lokaciju.
Ako adrese nema u OSM-u, traže se izričite koordinate ili točka odabrana na karti.
Model ih ne smije procijeniti.

Alat uspoređuje **sve mapirane objekte u obuhvatu** (uz najviše četiri istodobna
OTP izračuna), uključuje čekanje i predaju djeteta te vraća najbolju opciju
prema dolasku na posao i traženi broj alternativa. `top_k` je ukupan broj opcija
(pozitivan cijeli broj, zadano 4): najbolja opcija i tri alternative znači `top_k=4`, a top tri
znači `top_k=3`. Ograničavanje se primjenjuje tek nakon rangiranja cijelog kataloga.

Ako korisnik sam navede vrtiće između kojih bira, model ih šalje u
`kindergartens` (1–20 naziva, npr. `["Mala Vila", "Potok"]`) i rangiraju se
samo oni (`scope: "selected"`). Nazivi se traže istom pretragom po nazivu kao u
`prikazi_vrtice`, među objektima s potvrđenom lokacijom. Naziv koji odgovara
točno jednom objektu se prihvaća; više podudaranja ili nijedno vraća
`clarification_required` s `unresolved.kindergartens` (do osam kandidata s `id`,
nazivom i adresom). Model pita korisnika i ponavlja cijeli upit s `id`
odabranog kandidata umjesto naziva. `top_k` i dalje određuje koliko ih se
prikazuje.
Ako ima manje dostupnih ruta, alat vraća samo njih i točne brojeve pokrivenosti.

Oba alata koriste isti resurs `ui://kidsic/map-v35.html` iz `frontend/dist/mcp.html`.
Preporuka koristi istu sivu Leaflet/OSM kartu, boje oznaka, vodoravne kartice i
fullscreen prikaz kao `prikazi_vrtice`. Na karti i karticama su samo vraćenih
`top_k` vrtića u poretku dolaska na posao. Najbolja ruta je odabrana odmah;
odabir oznake, kartice ili retka prikazuje rutu druge opcije. Kartica prikazuje
rang, trajanje i dolazak. Detalji imaju dva taba: „Put” (dolazak na posao,
ukupno trajanje, presjedanja i vozni red po koracima uz predaju djeteta) i
„Vrtić” (isti detalji kao u gradskoj pretrazi). Kartica rute na karti navodi
rang i naziv odabrane opcije, a strelicama se prelazi na sljedeću ili prethodnu;
svaki odabir ponovno iscrtava rutu. Karta obuhvaća dom,
posao, sve vraćene vrtiće i dostupne geometrije odabrane rute. Nedostajuće
geometrije ne zamjenjuju se ravnim linijama.

Podaci dolaze kroz MCP bridge (`_meta.commute`): puni GeoJSON `locations`
sadrži isključivo rangirane objekte i njihove izvorne podatke. Model dobiva
sažetak bez koordinata doma/posla, GeoJSON-a i velikih geometrija. Iframe ne
poziva lokalni API. CSP dopušta OSM pločice i ugrađene resurse.

Nakon `npm --prefix frontend run build:mcp` ponovno pokrenuti MCP server i
osvježiti konektor. Discovery sada objavljuje jedan zajednički HTML resurs;
zaseban `day-mcp.html` i postavka `day_ui_path` više se ne koriste.

„Najbolji” ovdje znači najraniji dolazak među OTP-ovim vraćenim alternativama.
To ne potvrđuje radno vrijeme, dobnu prikladnost, kvalitetu vrtića, slobodna
mjesta ni mogućnost upisa. Učitani vozni red je 9. 10. – 8. 11. 2026., bez
kašnjenja uživo. Pogreška rutera ne zamjenjuje se procjenom.


### Šibenik

`prikazi_vrtice` i RAG alati prihvaćaju `city="Šibenik"`. Imenik uključuje
Brodaricu kao naselje Grada Šibenika, uz provjeru županije pri uvozu.
`preporuci_vrtice_usput` prihvaća `city="Šibenik"`, primjerice
`home="Svilajska ulica 20"`, `work="Ulica Velimira Škorpika 10"`,
`departure="2026-11-09T07:00"`, `mode="TRANSIT"`.
Šibenski ruter koristi fiksni port 18082 i indeks
`routing/data/sibenik/addresses.sqlite`. Datum mora biti između
2026-09-07 i 2027-06-07, a obje točke u šibenskom okviru.
Trenutačno se uspoređuju tri pregledana OSM objekta. Nepotpunu pokrivenost,
neprovjereno radno vrijeme i nepoznata slobodna mjesta treba navesti korisniku;
pobjednik je najbrži među dostupnim mapiranim kandidatima.
