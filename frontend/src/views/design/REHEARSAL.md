# Design review

This is an interactive standalone design exploration using the product's existing
shadcn Card, Button and Badge components. Stageshow's still-frame hierarchy and
realistic-content guidance informed the layout; no Stage animation or gold demo
was copied. The film animation gate does not apply to this prototype.

## Checked

- In-app Chromium browser: desktop at its default 1706 × 1238 viewport and a
  mobile override of 390 × 844; override reset afterward.
- Desktop split composition, numbered location cards and schematic map.
- Mobile list layout, mobile map layout and map selection via a card.
- Provider filtering updates the result count, cards and pins together.
- Favorite button updates the shortlist counter and shortlist filtering.
- Selecting a map pin updates the location callout.
- Empty text search displays recovery; recovery restores all sample locations.
- Parent guide opens and closes as a named native modal dialog.
- Keyboard-visible focus, native radio controls and reduced-motion CSS provided.
- Frontend test suite, lint, standalone build and single-file MCP build pass.

## Limits

All location names, addresses and map geometry are design samples. No real
geographic accuracy, vacancies, fees or age eligibility is implied. Favorites
are held in React state for this preview. Typography uses the system font stack without external font requests.
No device touch, screen reader session, native MCP host or reduced-motion browser
emulation was checked. Existing production location rendering is unchanged.

Open `/design.html` on the Vite dev server.

## Typography and imagery revision

Removed Fredoka, Nunito Sans, the Google Fonts request, the school illustration
component, hero artwork and decorative map trees following user feedback. The
preview now uses system sans-serif type and compact numbered location markers.
Rechecked the desktop and 390px layouts after this revision.
