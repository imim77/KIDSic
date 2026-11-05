# KIDSic MCP app

`prikazi_vrtice` je read-only MCP alat koji vraća postojeći GeoJSON za grad i
prikazuje kartu s vodoravnim karticama. Dob i program provjerava samo prema
aktualnim potvrđenim programima; ne potvrđuje pravo na upis ni slobodna mjesta.

## Pokretanje

Najprije pripremiti migriranu i uvezenu bazu prema [README-u](README.md).
Iz korijena repozitorija:

```sh
uv sync --locked
npm --prefix frontend ci
# Postaviti javni pk.… token u frontend/.env.local prema frontend/.env.example.
npm --prefix frontend run build:mcp
export DATABASE_URL=postgresql://kidsic:kidsic_local@localhost:55432/kidsic
uv run uvicorn KIDSic.api.mcp_server:create_app --factory --host 127.0.0.1 --port 8001
```

`KIDSic.mcp.server:create_app` ostaje kompatibilni ulaz za postojeće postavke.
Transport je u `api/mcp_server.py`, grupa alata u `api/location_tools.py`,
a HTML resurs u `api/apps/map_resource.py`.

Streamable HTTP endpoint je `http://127.0.0.1:8001/mcp`. Server pri pokretanju
učitava `frontend/dist/mcp.html` i otvara jedan pool baze. Ako build nedostaje,
pokretanje završava jasnom porukom. `KIDSIC_UI_PATH` može zadati drugi put do
izgrađenog HTML-a, npr. u deploymentu. Nakon promjene builda ponovno pokrenuti
server. Pakiranje Python wheela samo ne uključuje frontend; deployment mora
isporučiti taj HTML. Ne pokreću se migracije niti uvoz pri startu.

`npm run build` čisti frontend `dist`; ako se gradi i samostalni preview, zatim
pokrenuti `build:mcp`. Javni Mapbox token ugrađuje se u HTML. Token ograničen na
URL mora dopuštati stvarni sandbox origin hosta; lokalni preview ne potvrđuje da
će ista ograničenja raditi u ChatGPT-u. Privatni `sk.…` token nikad ne koristiti.

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
- „Montessori u Zagrebu za dijete od 2 godine.” → `{"city":"Zagreb","age_months":24,"program":"Montessori"}`.
- „Tražim Čarobnu kućicu.” → pitati za grad, bez pretrage po pretpostavljenom gradu.
- „Prikaži mi vrtiće u Splitu.” → poruka da su podržani Zagreb, Varaždin i Rijeka, bez čitanja baze.
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
koordinata nisu uključeni, a svaki rezultat nosi `distance_m`. Udaljenost nije
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

Opcionalni `age_months` je cijeli broj od 0 do 216 ili `null`/izostavljeno za
pretragu bez dobi. AI klijent pretvara izričitu dob u mjesece: 2 godine = 24,
2 godine i 6 mjeseci = 30. Nula je valjana vrijednost, nije izostavljena dob.
Ako dob nije jasna, klijent pita za mjesece; ne zaključuje je iz riječi „jaslice”.
Program se može pretraživati i bez dobnog filtra, bez tvrdnje o prikladnosti za dob.

Opcionalni `program` je naziv ili dio naziva programa, triman, do 200 znakova;
prazno/izostavljeno znači bez tog filtra. Podudaranje je literalno i zanemaruje
velika slova i hrvatske dijakritike. `name` i dalje označava ustanovu/objekt.
Programi se ne zaključuju iz naziva ustanove, kontakata ili pravila sufinanciranja.

`include_unknown` je boolean, zadano `true`. `false` se šalje samo na izričit
zahtjev „samo potvrđeni”. Uz dob/program rezultati su podijeljeni:

- `confirmed`: isti aktualni program zadovoljava traženi naziv programa i dob
  (donja granica uključiva, gornja isključiva), za svaki zadani kriterij.
- `unknown`: nema aktualnog dokaza za traženi program ili nedostaje njegova
  potpuna dobna granica. Drugi objavljeni program ne dokazuje da traženi ne postoji.
- Poznati potpuni rasponi traženog programa koji ne uključuju dob ne ulaze u
  rezultat; jedan drugi program ne smije poslužiti kao dobni dokaz za traženi.

Bez dobi i programa status je `not_evaluated`, a `include_unknown` nema učinka.
`metadata.confirmed` i `metadata.unknown` broje vraćene skupine. UI prikazuje
oznaku samo za potvrđena podudaranja, bez oznake nepoznatih uvjeta i naslova skupina. Gornji red
kriterija nije prikazan; primijenjeni kriteriji i brojevi ostaju u odgovoru alata. Detalji navode raspon, datum provjere, izvor i je li dokaz za
ustanovu ili konkretan objekt. Podatak za ustanovu ne jamči provedbu u svakom
objektu. Potvrđeno podudaranje nije jamstvo mjesta ni upisa.

Trenutačno u lokalnoj snimci imenika nema potvrđenih zapisa u tablici `program`.
Pretraga s dobi/programom zato vraća nepoznate uvjete; `include_unknown: false`
vraća nulu. Implementacija ne dodaje izmišljene programe. Potvrđena i rubna
podudaranja provjeravaju se sintetičkim podacima samo u rollback testnoj bazi.

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

Uspješan rezultat uvijek vraća primijenjeni `city`, `name`, `provider_kind`, `area`, `age_months`, `program` i `include_unknown`. UI čuva kriterije
pri ponovnom pokušaju i briše prethodni odabir pri novom upitu, bez gornjeg reda
filtra iznad karte. Nula rezultata prikazuje praznu kartu s pozivom da se naziv provjeri ili
skrati; server i UI ne proširuju pretragu automatski. Za sve vrste izostaviti `provider_kind` ili poslati `null`; za sve nazive
izostaviti `name`. Novi poziv bez vrste ili područja ne nasljeđuje te filtre prethodne pretrage.

Tumačenje prirodnog jezika i pitanje za nedostajući grad obavlja AI klijent
prema opisu alata i uputama servera. Python server validira strukturirane
argumente i izvršava determinističku pretragu; nema zasebnog LLM poziva ni
novog chat polja u web aplikaciji. RAG kontekst dostupan je kroz zaseban alat
`dohvati_kontekst_vrtica`; usporedba i vodič za upis još nisu implementirani.

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

Resurs `ui://kidsic/map-v16.html` ima MIME `text/html;profile=mcp-app`. Moderni
`_meta.ui.resourceUri` i kompatibilni `openai/outputTemplate` povezuju ga s alatom.
Uspješan rezultat ima sažetak `structuredContent: {city, name, provider_kind, area, age_months, program, include_unknown, metadata}`, uz deklarirani
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
povezati konektor kako bi host preuzeo URI resursa v16 te pokrenuti novi poziv
alata.
Resurs deklarira CSP za Mapbox API, događaje, tiles i blob/data resurse. Host mora
dopustiti Mapbox blob worker i WebGL; u suprotnom ostaju dostupne kartice. UI je
jedan HTML bez relativnih JS/CSS zahtjeva. Kod budućih breaking promjena resursa
promijeniti verziju URI-ja zbog host cachea.

### MCP Inspector: kartice su vidljive, karta je prazna

U MCP Inspectoru 2.13.0 kartica **Apps** učitava ovaj UI, ali njegov sandbox
postavlja `worker-src 'none'`. Mapbox GL JS zahtijeva Web Workere za obradu
pločica i GeoJSON-a pa karta ostaje prazna iako se kartice i kontrole učitaju.
To ograničenje hosta ne uklanja dodavanje `blob:` u `resourceDomains`: ta lista
ne upravlja direktivom `worker-src`. Ni CSP meta tag u našem HTML-u ne može
ublažiti politiku koju je host već primijenio.

Za dijagnostiku u pregledničkim razvojnim alatima odabrati unutarnji iframe
aplikacije i pregledati njegov `meta[http-equiv="Content-Security-Policy"]`.
Ako sadrži `worker-src 'none'`, prikaz podloge treba provjeriti u MCP Apps hostu
koji dopušta blob workere ili u samostalnom Vite pregledu opisanom u README-u.
Samostalni pregled potvrđuje kartu, ali ne potvrđuje MCP bridge. Zasebno
provjeriti da Apps prikaz prima grad i stvarne kartice iz rezultata alata.

Vidi [prijedlog podrške za workere u MCP Apps CSP-u](https://github.com/modelcontextprotocol/ext-apps/issues/566)
i [Mapboxove CSP zahtjeve](https://docs.mapbox.com/mapbox-gl-js/guides/security-and-testing/).

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
provjeru u ChatGPT-u: povezati server, isprobati oba grada i upit bez grada,
potvrditi podlogu, odabir kartica i izlazak iz fullscreena.

Reference: [MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview),
[UI povezivanje u ChatGPT-u](https://developers.openai.com/plugins/build/chatgpt-ui).

Scenariji za provjeru filtra područja i nastavaka razgovora nalaze se u
[conversational_area.md](tests/fixtures/conversational_area.md).

Scenariji za dob i programe: [conversational_age_program.md](tests/fixtures/conversational_age_program.md).
