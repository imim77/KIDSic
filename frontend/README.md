# KIDSic frontend

React/TypeScript prikaz povezuje Mapbox kartu, listu objekata i filtre nad stvarnim podacima iz `GET /api/locations`.

- `src/views/index.html`: HTML ulaz.
- `src/views/welcome/`: React prikaz, njegov stil i ulazna skripta.
- `src/shared/locations/`: ugovor podataka, dohvat, filtri, lista i izvori.
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

Postaviti javni `VITE_MAPBOX_ACCESS_TOKEN` u `.env.local`; Vite čita tu datoteku iz ove mape. Bez tokena dostupna je lista. Nakon promjene tokena ponovno pokrenuti razvojni server ili ponoviti produkcijski build.

API mora biti zasebno pokrenut na portu 8000. Za drugi port koristiti, primjerice, `KIDSIC_API_TARGET=http://127.0.0.1:18000 npm run dev`. Produkcijski hosting mora sam usmjeriti `/api` na backend.

Detaljne [upute za bazu i API](../README.md#web-prikaz-lokacija) i [ugovor lokacija](../LOCATION_API.md) nalaze se u korijenu repozitorija. MCP Apps SDK i HTML pakiranje još nisu implementirani.
