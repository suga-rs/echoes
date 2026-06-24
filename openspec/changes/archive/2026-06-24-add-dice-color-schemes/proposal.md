## Why

The 3D d20 has a single hardcoded look (pale-gray body, dark numbers). Players who
have invested in a character and a theme have no way to personalize the dice, the
one piece of interactive 3D in the app. A small set of color schemes is a cheap,
self-contained piece of player expression that slots into the appearance settings
we already have.

## What Changes

- Add a **"Color del dado"** control to the existing settings panel, offering three
  selectable schemes for the 3D d20:
  - **Marfil** (default) — pale-gray body, dark numbers, satin finish (the current look).
  - **Obsidiana** — charcoal body, bone-white numbers, glossy finish.
  - **Esmeralda** — deep-green body, mint numbers, matte-metal finish.
- Each scheme owns the dice **body color**, **number-label color**, and **surface
  finish** (metalness/roughness).
- The per-result emissive glow (gold = crit success, emerald = success, gray =
  failure, red = crit failure) stays **semantic** and is NOT overridden by a scheme,
  so result feedback always reads the same regardless of chosen colors.
- Persist the chosen scheme locally so it survives reloads, alongside the existing
  appearance preferences.

## Capabilities

### New Capabilities
- `dice-appearance`: Player-selectable color scheme for the 3D d20 (body color,
  number color, surface finish), persisted locally, while the semantic result glow
  remains fixed.

### Modified Capabilities
- `reading-preferences`: The appearance settings surface now also exposes the dice
  color control, so the "Settings surface for appearance" requirement is broadened to
  include it.

## Impact

- **Frontend only.** No backend, API, or data-model changes.
- `frontend/src/store/settings-store.ts` — new `DiceScheme` type, scheme palette map,
  persisted state field + setter (reuses existing zustand `persist`).
- `frontend/src/components/settings-sheet.tsx` — one additional `OptionGroup`.
- `frontend/src/components/dice-3d-canvas.tsx` — reads the chosen scheme from the
  store and applies body/number/finish; the scheme must be added to the render
  `useEffect` deps.
- Tests: extend existing `settings-sheet` and `settings-store` test coverage.
