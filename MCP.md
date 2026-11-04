# KIDSic MCP app

`prikazi_vrtice` je read-only MCP alat koji vraća postojeći GeoJSON za grad i
prikazuje kartu s vodoravnim karticama. Ne procjenjuje upisne uvjete, dobnu
prikladnost, kapacitet ili slobodna mjesta.

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
- „Tražim Čarobnu kućicu.” → pitati za grad, bez pretrage po pretpostavljenom gradu.
- „Prikaži mi vrtiće u Splitu.” → poruka da su podržani Zagreb, Varaždin i Rijeka, bez čitanja baze.
- „Prikaži mi vrtiće.” → AI pita „U kojem gradu želiš prikaz vrtića?” prije poziva.

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

Uspješan rezultat uvijek vraća primijenjeni `city`, `name` i `provider_kind`. UI ih prikazuje
iznad karte, čuva ih pri ponovnom pokušaju i briše prethodni odabir pri novom
upitu. Nula rezultata prikazuje praznu kartu s pozivom da se naziv provjeri ili
skrati; server i UI ne proširuju pretragu automatski. Za sve vrste izostaviti `provider_kind` ili poslati `null`; za sve nazive
izostaviti `name`. Novi poziv bez vrste ne nasljeđuje vrstu prethodne pretrage.

Tumačenje prirodnog jezika i pitanje za nedostajući grad obavlja AI klijent
prema opisu alata i uputama servera. Python server validira strukturirane
argumente i izvršava determinističku pretragu; nema zasebnog LLM poziva ni
novog chat polja u web aplikaciji. Dob, područje, RAG, usporedba i
vodič za upis nisu parametri ovog koraka.

Upute servera i opis alata zahtijevaju ovaj alat za prikaz vrtića. Svaki poziv je
povezan s UI resursom u definiciji alata i metapodacima rezultata. Server ipak ne
može prisiliti proizvoljan AI klijent da pozove alat ili renderira MCP Apps;
te dvije stvari treba potvrditi u ciljnom klijentu. Tekstualni MCP klijent može
pročitati rezultat, ali ne može prikazati interaktivnu kartu.

## Ugovor UI-ja i provjera

Resurs `ui://kidsic/map-v11.html` ima MIME `text/html;profile=mcp-app`. Moderni
`_meta.ui.resourceUri` i kompatibilni `openai/outputTemplate` povezuju ga s alatom.
Uspješan rezultat ima sažetak `structuredContent: {city, name, provider_kind, metadata}`, uz deklarirani
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
visinu iframea kroz `100dvh`. MCP kartice visoke su 92 px; fullscreen koristi
visinu dodijeljenog prozora. Klik na karticu traži fullscreen i otvara popis,
detalje i kartu u stupcima (ispod 1100 px detalji prekrivaju popis, ispod 700 px
kartu). Detalji prikazuju samo podatke iz izvora i navode što nije poznato;
vanjske poveznice otvaraju se kroz `ui/open-link`. Nakon nadogradnje ponovno
povezati konektor kako bi host preuzeo URI resursa v11 te pokrenuti novi poziv
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
