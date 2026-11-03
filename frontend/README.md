# KIDSic frontend

React/TypeScript UI za MCP app prikazuje Mapbox kartu s vodoravnim karticama, detaljima i fullscreen kontrolom nad stvarnim podacima iz `GET /api/locations`. Prikaz zauzima prostor hosta; nema zasebnu navigaciju, legendu ili filtre.

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

Detaljne [upute za bazu i API](../README.md#lokalni-pregled-mcp-sučelja) i [ugovor lokacija](../LOCATION_API.md) nalaze se u korijenu repozitorija. MCP Apps SDK i HTML pakiranje još nisu implementirani.
