# KIDSic frontend

React/TypeScript UI za MCP app prikazuje Mapbox kartu s vodoravnim karticama, detaljima i fullscreen kontrolom nad stvarnim podacima iz `GET /api/locations`. Prikaz zauzima prostor hosta; nema zasebnu navigaciju, legendu ili filtre.

Tailwind CSS v4 uključen je preko službenog `@tailwindcss/vite` plugina u oba
Vite builda. Klase se pišu izravno u TSX-u (npr. `w-full h-dvh p-2` ili
`min-w-0 flex-1`). Zajednički `src/shared/theme.css` izlaže postojeće boje kao
`text-ink`, `text-muted`, `text-accent`, `border-border` i `bg-surface` tokene.
Skeniranje klasa obuhvaća cijeli `src`, uključujući MCP ulaz. Tema i utilities
učitavaju se bez Preflight reseta kako bi se očuvali postojeći Mapbox i osnovni
stilovi. Specifični responsive stilovi karte, kartica i fullscreena ostaju u CSS-u.

- `src/views/index.html`: HTML ulaz.
- `src/views/welcome/`: React prikaz, njegov stil i ulazna skripta.
- `src/shared/locations/`: ugovor podataka, dohvat, kartice, carousel i izvori.
- `src/shared/explorer/`: zajednički okvir, detalji i prošireni prikaz.
- `src/shared/map/`: Mapbox lifecycle, GeoJSON slojevi i odabir objekta.
- `src/shared/`: zajednička tema i resursi.
- `public/`: statičke datoteke.

```sh
npm ci
cp .env.example .env.local
npm run dev
npm test
npm run build
npm run lint
```

Postaviti javni `VITE_MAPBOX_ACCESS_TOKEN` u `.env.local`; Vite čita tu datoteku iz ove mape. Bez tokena dostupne su kartice. Nakon promjene tokena ponovno pokrenuti razvojni server ili ponoviti produkcijski build.

API mora biti zasebno pokrenut na portu 8000. Za drugi port koristiti, primjerice, `KIDSIC_API_TARGET=http://127.0.0.1:18000 npm run dev`. Produkcijski hosting mora sam usmjeriti `/api` na backend.

`npm run build:mcp` gradi `dist/mcp.html` sa svim skriptama i stilovima ugrađenima u HTML. Ulaz je `src/views/mcp/mcp.html`; koristi službeni MCP Apps SDK, prima grad i sažetak iz `structuredContent` te GeoJSON iz `_meta.locations` i traži fullscreen od hosta. Ne poziva `/api` niti koristi početni Zagreb. Samostalni `npm run build` čisti `dist`, pa MCP build pokrenuti nakon njega ako trebaju oba prikaza.

Detaljne [upute za bazu i API](../README.md#lokalni-pregled-mcp-sučelja), [ugovor lokacija](../LOCATION_API.md) i [MCP povezivanje](../MCP.md) nalaze se u korijenu repozitorija.
