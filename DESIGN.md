# KIDSic design system

The KIDSic MCP app adopts the visual language of
[maggie-app.com](https://maggie-app.com/): saturated pastel fields, one deep
green ink colour for all text and outlines, chunky uppercase display type, a
handwritten script accent, pill controls and a hard offset "sticker" shadow.

This document supersedes the earlier design preview (system fonts, no rounded
display type, no illustration), which has been removed. Croatian copy, the data honesty rules in `MCP.md` and the
existing component structure stay as they are.

## What "the same" covers

Copied exactly: colour values, type roles and scale ratios, letter spacing,
corner radii, shadow geometry, pill/chip/card shapes and the colour rotation
pattern.

Not copied: Maggie's name, wordmark, ghost mascot, photography, phone mockups,
marketing copy or sticker illustrations. These are their brand assets, not
design tokens. KIDSic keeps its own name and uses no mascot unless one is drawn
for it.

## Reference measurements

Measured on 2026-11-04 from the live Framer site (computed styles at 1440×900
and 375×812). Values below are those measurements unless marked *derived*.

### Colour

Maggie exposes these as Framer tokens. KIDSic names them by role.

| Token | Hex | Role on Maggie | KIDSic role |
| --- | --- | --- | --- |
| `--ink` | `#03594d` | All text, outlines, shadows | Text, borders, shadow, focus ring |
| `--ink-soft` | `#89a9a1` | Secondary marks | Decorative/disabled only (fails text contrast) |
| `--ink-wash` | `#02594d33` | Translucent ink | Hairlines, map overlays |
| `--cream` | `#f9f8f4` | Card and panel surface | Card, sheet and notice surface |
| `--mint` | `#82eda6` | Page background, hero | App background, primary pill |
| `--lemon` | `#ffff94` | Section panels | Rotation colour, highlight |
| `--sky` | `#aefbff` | Section panels, "Add venue" pill | Rotation colour |
| `--blush` | `#fccddc` | Feature card, "About" pill | Rotation colour |
| `--lilac` | `#f6bbfd` | Splash, "FAQs" pill | Rotation colour |
| `--violet` | `#c88cfd` | In-app selected chip, map pins, primary button | Map pins, selected state |
| `--apricot` | `#fdc068` | Side panels | Rotation colour |
| `--orange` | `#ff9124` | Accent | Clusters (*derived*) |
| `--blue` | `#589af0` | Category tile | Rotation colour |
| `--rose` | `#fc5681` | Accent | Error marker (never as text colour) |
| `--lime` | `#d8e268` | Accent | Unused, reserved |

Rules seen on the site:

- Text is always `--ink`. There is no black, grey or white body text. The only
  exception is a display word set in `--cream` on a coloured panel.
- Backgrounds are flat fills. No gradients, no blur, no glassmorphism.
- Neighbouring elements never share a fill. Nav pills cycle
  lilac → blush → mint → sky; sections cycle mint → lemon → blush → sky →
  cream.

### Typography

| Role | Maggie font | Size (desktop) | Line height | Tracking | Case |
| --- | --- | --- | --- | --- | --- |
| Display XL | BN Dime Display | 180px | 0.8 | 1% (1.8px) | Upper |
| Display L | BN Dime Display | 120px | 0.8 | 1% (1.2px) | Upper |
| Heading | BN Dime Display | 48px | 0.9 | 0.5px | Upper |
| Subheading | BN Dime Display | 32px | 0.9 | 0.5px | Upper |
| Label / pill | BN Dime Display | 14px | 1.0 | 0.5px | Upper |
| Script accent | Homemade Apple | 25px (14–20px small) | ~1.15 | 0.25px | As written |
| Body / micro | Helvetica Neue, sans-serif | 9–16px | normal | ~2% | Sentence |

Everything in BN Dime Display is weight 400; the face itself is heavy. Mobile
uses fit-to-width display text, so headings scale with the container rather
than following fixed breakpoints. Line height below 1 is intentional: stacked
display lines touch.

The script face appears once per section as a small aside above or below a
display headline ("meet maggie", "You're welcome!"). It is never used for UI
labels or data.

### Shape

| Element | Radius |
| --- | --- |
| Pills (nav, buttons, chips) | `100px` |
| Cards, phone frames | `20px` |
| Thumbnails | `10px` |
| Large panels | `40px`–`60px` |
| Section panels | Bottom-only `0 0 60px 60px` |
| Arch / dome shapes | `1000px 1000px 0 0` |

### Shadow

The signature is a solid, unblurred shadow offset down-left, in `--ink`:

```css
--shadow-sm: -3px 3px 0 0 var(--ink);  /* pills, chips */
--shadow-md: -4px 4px 0 0 var(--ink);  /* thumbnails, small cards */
--shadow-lg: -5px 6px 0 0 var(--ink);  /* phone frames, feature cards */
--shadow-xl: -8px 8px 0 0 var(--ink);  /* hero object */
```

Maggie's pills have no border; the shadow alone gives them weight. Larger
cards and thumbnails add a `2px solid var(--ink)` outline (visible in the
screenshots, *derived* width). There are no soft drop shadows anywhere.

### In-app screens

The phone mockups show Maggie's own product UI, which is the closest analogue
to the KIDSic map view:

- Cream (`--cream`) screen background, ink text, ink outlines.
- Map: light grey basemap with green parks; pins are violet teardrops.
- Result header: count in display type ("26 Found"), centred above a chip row.
- Filter chips: cream pills with ink text; the selected chip is filled violet.
- Category tiles: square, `20px` radius, one rotation colour each.
- Primary button: full-width violet pill ("Apply Filters"), secondary is a
  cream pill ("Reset Filters").
- Detail card: photo on top, display-type title, small body text, icon
  actions (share, favourite) top right.

## Applying it to KIDSic

The MCP view is a 520px (480px narrow) inline iframe that can go fullscreen.
Marketing-scale type does not fit, so KIDSic uses the Maggie ratios on a
smaller base.

### Type scale for the MCP view

| Role | Font | Size | Use |
| --- | --- | --- | --- |
| Title | Titan One | 18px / 1.25, 1% | Card title, notice heading |
| Label | Titan One | 13px / 1, 0.5px, upper | Buttons, chips |
| Body | Helvetica Neue stack | 13px | Addresses, notices |
| Micro | Helvetica Neue stack | 12px | District, map attribution |

The display face is **Titan One** (OFL, `@fontsource/titan-one`), not BN Dime
Display. Rendered side by side on maggie-app.com, BN Dime Display has no ć, đ,
š or ž glyphs, so it cannot set Croatian names even with a licence. Titan One
was the closest of six free candidates and covers Latin Extended-A.

The script face is **not used**. Homemade Apple ships only a basic Latin subset,
so Croatian text would mix in fallback glyphs.

Card titles are not uppercased: kindergarten names are proper nouns and long,
and uppercase hurts their legibility at 18px. Labels, chips and counts are
uppercase as on Maggie.

### Components

**App frame** (`.kindergarten-explorer`, `welcome.css`). Mint page background
around a cream map with a `2px` ink outline and `--shadow-lg`; `20px` radius in
MCP, `32px` standalone, no outline, shadow or radius in fullscreen.

**Map** (`KindergartenMap`, `LocationLayer.ts`). Leaflet with an OpenStreetMap
basemap. Provider colours distinguish points; the selected point is larger
with a `4px` ink stroke. Clusters use cream circles with ink counts.
OpenStreetMap attribution stays visible below the cards.

**Location card** (`LocationCard.tsx`). Cream fill, `2px` ink outline, `20px`
radius, `--shadow-md`. 92px tall in MCP. The thumbnail is a `10px`-radius tile
whose fill rotates through lemon, sky, blush, lilac, apricot by card index,
with the building icon in ink. When selected, the card lifts
(`translate(2px, -2px)`), its shadow grows to `--shadow-lg` and its tile turns
violet to match the selected pin (*derived*). Text stays on cream.

**Pill buttons** (`.text-button`, carousel arrows). `100px` radius, no border,
`--shadow-sm`. Text buttons use lemon fill and label type; icon buttons use
mint. Hover turns the fill lemon. Pressed: `var(--press)` and
`box-shadow: none`, so the pill sits on its shadow. Violet is never used
behind text.

**Expanded explorer** (`LocationList`, `LocationDetails`). Choosing a card
requests fullscreen and lays out a results column, a details column and the
map, after Booking's fullscreen app layout. Below 1100px the details cover the
list; below 700px they cover the map and the card deck stays. The details hero
is a violet tile with the building icon, since sources carry no photos; there
are no ratings or prices, and a lemon note says what the data cannot tell.

**Fullscreen toggle** (`fullscreen.css`). 46px mint circle, no border,
`--shadow-sm`, ink icon, same hover and press behaviour.

**Notices** (`.explorer-notice`, `.map-message`). Cream card, `2px` ink
outline, `20px` radius, `--shadow-md`. Heading in the title style; body in the
body style. Error notices use a rose dot marker, never rose text.

**Map controls** (Leaflet zoom). Mint pill group with `--shadow-sm` and
ink-wash dividers. The zoom buttons use ink-coloured plus and minus symbols.

### Motion

Maggie is built in Framer with scroll-linked reveals and springy hovers. The
MCP view needs only state transitions: `transform` and `box-shadow` over
`120ms ease-out` for press and select. Disable them under
`prefers-reduced-motion: reduce`. Hover timings on Maggie were not measured.

### Accessibility

Contrast of `--ink` text (WCAG 2.x ratios, computed from the hex values):

| Background | Ratio | Body text |
| --- | --- | --- |
| Cream `#f9f8f4` | ~7.8 | Pass AA/AAA |
| Mint `#82eda6` | ~5.7 | Pass AA |
| Violet `#c88cfd` | ~3.4 | Large/bold labels only |
| Lemon, sky, blush, lilac | > 7 | Pass |

Consequences:

- `--ink-soft` `#89a9a1` (~2.4 on cream) never carries information. Secondary
  text such as addresses stays `--ink` and is distinguished by size and weight.
- Violet fills appear only behind icons and on pins. Selection is also shown by
  `aria-pressed`, the lift and the larger shadow.
- Focus ring: `3px solid var(--ink)`, `3px` offset, replacing the red accent.
- Map pins distinguish selection by size and stroke, not hue alone.

## Implementation notes

- **Tokens** live in `frontend/src/mvvm/tailwind.css`. The shadcn role names
  stay and point at the palette: `--accent` → violet, `--border` → ink,
  `--surface` → cream, `--secondary` → lemon, `--muted` → ink. Tailwind gets a
  `font-display` utility.
- **Fonts.** `vite.mcp.config.ts` builds one self-contained HTML file inside a
  CSP-sandboxed iframe, so Titan One is bundled from `@fontsource/titan-one`
  and inlined by `vite-plugin-singlefile` (about +41 kB gzipped). Nothing is
  fetched from Google Fonts or Framer.
- **Map colours.** Marker backgrounds use shared `providerColors`; borders
  and clusters use CSS theme tokens.

## Open questions

1. **Basemap style.** Standard OpenStreetMap tiles use a greyscale CSS filter;
   provider markers and controls retain their colours.
2. **Host dark mode.** Maggie has no dark theme. The MCP view paints its own
   background, so it stays light inside dark hosts. Confirm that is acceptable.
3. **Script accent.** Bring back a handwritten aside only with a face that
   covers Croatian (for example Caveat), or leave it out.
