# KIDSic frontend

React/TypeScript UI za MCP app prikazuje Leaflet/OpenStreetMap kartu s vodoravnim karticama i fullscreen kontrolom nad stvarnim podacima iz `GET /api/locations`. Prikaz zauzima prostor hosta; nema zasebnu navigaciju, legendu ili filtre.

Tailwind CSS v4 uključen je preko službenog `@tailwindcss/vite` plugina u oba
Vite builda. Klase se pišu izravno u TSX-u (npr. `w-full h-dvh p-2` ili
`min-w-0 flex-1`). Zajednički `src/shared/theme.css` izlaže postojeće boje kao
`text-ink`, `text-muted-foreground`, `text-primary`, `border-border` i `bg-surface` tokene.
Skeniranje klasa obuhvaća cijeli `src`, uključujući MCP ulaz. Tema i utilities
učitavaju se bez Preflight reseta kako bi se očuvali postojeći Leaflet i osnovni
stilovi. Specifični responsive stilovi karte, kartica i fullscreena ostaju u CSS-u.

Kartice koriste lokalne shadcn/ui komponente `Card`, `Button` i `Badge` iz
`src/shared/ui`, dodane službenim CLI-jem iz `@shadcn` registra. Konfiguracija je
u `components.json` (`new-york`, Radix, Lucide). Komponente koriste samo Radix Slot
primitivu, `class-variance-authority` i službeni `cn` za spajanje klasa; nisu
potrebne sve Radix kontrole. Alias `@/` pokazuje na `src/` u oba builda i testovima.
Nove komponente dodavati izričito iz istog registra, npr.
`npx shadcn@latest add @shadcn/separator`, i pregledati generirani kod.

Red kartica koristi postojeći native scroll-snap: širina je do 320 px na većim
ekranima i do 280 px na mobitelu, a visina 132 px. Kružni gumbi na rubovima reda
ne mijenjaju odabir karte. Naziv i adresa mogu biti vizualno skraćeni; puni tekst
ostaje u pristupačnom nazivu i title atributu. Sličica je neutralna ikona jer izvori
ne sadrže fotografije vrtića.

MCP prikaz ima kompaktnije kartice: visina 92 px i širina do 268 px. Inline
okvir traži 520 px visine (480 px do širine 420 px), neovisno o početnoj visini
hostova iframea. SDK automatski prijavljuje visinu hostu. Fullscreen i dalje
ispunjava dodijeljeni prozor.

- `src/views/index.html`: HTML ulaz.
- `src/views/welcome/`: React prikaz, njegov stil i ulazna skripta.
- `src/shared/locations/`: ugovor podataka, dohvat, kartice i carousel.
- `src/shared/explorer/`: zajednički okvir i prošireni prikaz.
- `src/shared/map/`: Leaflet lifecycle, grupirane oznake i odabir objekta.
- `src/shared/motion/`: GSAP ulazne animacije (`useEntrance`) i sklopivi odjeljci (`Disclosure`).
- `src/shared/`: zajednička tema i resursi.
- `public/`: statičke datoteke.

Animacije koriste [GSAP](https://gsap.com) i `@gsap/react` (`useGSAP` čisti
animacije pri unmountu). Kartice, popis i detalji odabranog vrtića ulaze
postupno: mijenjaju se samo prozirnost i pomak, a inline stilovi brišu se na
kraju, da ostanu CSS hover i press stanja i da detalji mogu primiti fokus.
Animira se omotač (`li`), ne kartica s vlastitim CSS prijelazom.
Sklopivi odjeljci (npr. „Tarife, olakšice i uvjeti”) ostaju nativni `<details>`
radi tipkovnice, pretrage stranice i čitača zaslona; `Disclosure` samo glatko
mijenja visinu i zatvara element tek kad animacija završi. Uz
`prefers-reduced-motion: reduce` ili bez `matchMedia` (npr. u testovima)
sadržaj se odmah prikazuje u konačnom stanju. GSAP koristi vlastitu besplatnu
[standardnu licencu](https://gsap.com/standard-license), a ne OSS licencu.
Dopušta komercijalnu uporabu na web-stranicama i aplikacijama; zabranjuje samo
alate za izradu vizualnih animacija bez koda koji konkuriraju Webflowu. GSAP povećava MCP bundle s
otprilike 208 na 236 KB gzip.

```sh
npm ci
npm run dev
npm test
npm run build
npm run lint
```

Karta koristi OpenStreetMap pločice bez API tokena, WebGL-a ili Web Workera. Podloga zahtijeva internetsku vezu; kartice ostaju dostupne ako dohvat pločica ne uspije.

API mora biti zasebno pokrenut na portu 8000. Za drugi port koristiti, primjerice, `KIDSIC_API_TARGET=http://127.0.0.1:18000 npm run dev`. Produkcijski hosting mora sam usmjeriti `/api` na backend.

`npm run build:mcp` gradi `dist/mcp.html` sa svim skriptama i stilovima ugrađenima u HTML. Ulaz je `src/views/mcp/mcp.html`; koristi službeni MCP Apps SDK, prima grad i sažetak iz `structuredContent` te komprimirani GeoJSON iz `_meta.locations` (`gzip+base64`) i traži fullscreen od hosta. Dekompresija čuva sve objekte i izvore te koristi preglednički `DecompressionStream`, bez workera ili dodatnog dohvata. Ne poziva `/api` niti koristi početni Zagreb. Samostalni `npm run build` čisti `dist`, pa MCP build pokrenuti nakon njega ako trebaju oba prikaza.

Detaljne [upute za bazu i API](../README.md#lokalni-pregled-mcp-sučelja), [ugovor lokacija](../LOCATION_API.md) i [MCP povezivanje](../MCP.md) nalaze se u korijenu repozitorija.

Kartice prikazuju naziv, adresu i dostupnu gradsku četvrt. Oznaka pružatelja,
napomena o sjedištu/koordinatama i zaseban pogled detalja uklonjeni su iz UI-ja.
Odabir kartice i oznake na karti ostaje zajednički.

Cijelu površinu kartice pokriva jedan nativni shadcn gumb: sličica, naziv,
adresa i prazni prostor biraju isti objekt, uz Enter/Space podršku i jedan
tabulatorni korak po kartici.
