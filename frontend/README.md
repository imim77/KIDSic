# KIDSic frontend

Vite/React početni prikaz organiziran prema FOIHireloomu:

- `src/views/index.html`: HTML ulaz.
- `src/views/welcome/`: React prikaz, njegov stil i ulazna skripta.
- `src/shared/`: zajednička tema i resursi.
- `public/`: statičke datoteke.

```sh
npm ci
npm run dev
npm run build
npm run lint
```

Početni prikaz ne poziva backend. MCP Apps SDK i pakiranje samostalnih HTML prikaza dodaju se prilikom implementacije MCP korisničkog sučelja.
