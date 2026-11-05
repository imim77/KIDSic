# KIDSic design preview

## Research and intent

The existing `KindergartenExplorer` is a map with a horizontal card rail. MCP
results come from the host; the standalone view uses the location API. Sources
supply names, addresses, provider kinds and sometimes coordinates, but do not
confirm vacancies, prices, ratings or ages. This design must not invent those
claims or replace the working result flow with fixtures.

## Approaches and decision

A direct reskin would be small but would make a visual exploration affect both
production entry points. A separate interactive design route lets the user review
the richer layout first. Use the second approach, reusing installed shadcn
Button/Card/Badge and Lucide icons. No new package or backend dependency.

## Direction

A clean, friendly directory for parents. The user rejected the rounded display
fonts and illustrative school artwork. Use the native system sans-serif family
throughout, with a stronger headline and readable utility text. Keep sky blue,
sunshine yellow and soft corners for a restrained child-friendly identity.
Remove the hero scene and school thumbnails. Small numbered markers connect
cards to the map without invented photography or decorative illustrations.

The preview lives at `/design.html`, at 1200px desktop and 390px mobile. The main
story is choosing a city, narrowing provider types, selecting a card and seeing
its matching pin. Saving works within the session. List and map views are
available on mobile. All locations and illustrations are labeled design samples;
the map is schematic. No age, availability, pricing or review claims.

## Scope and open questions

This is a reviewable design prototype, not the production MCP result renderer.
Croatian copy matches the existing app. Favorites are a proposed UI interaction
and have no persistence. Final API integration and host fullscreen behavior are
outside this design pass. No live map changes are needed.
