## Why

The narrator text is the heart of Echoes, but its typography is fixed (serif
Crimson Text at one size) with no way for players to adjust it. Readers with
dyslexia or low vision, or anyone who simply prefers a different face or size,
have no recourse. There is also no settings surface at all — the only appearance
control (theme) is a lone header toggle.

## What Changes

- Add a **settings sheet** (slide-over panel opened by a gear icon) that
  consolidates appearance controls in one place.
- Add a **narrator font** preference with three choices: serif (Crimson Text,
  default), sans (Inter), and a dyslexia-friendly option (Atkinson Hyperlegible).
- Add a **narrator text size** preference (small / medium / large).
- Move the existing **theme** toggle into the settings sheet to declutter the
  header and group all appearance controls.
- Persist preferences locally (survive reloads) and apply them live to the
  narrator text via CSS variables.
- Apply the chosen **font family** (not size) to the other narrative game-text
  surfaces — player actions, option buttons, inventory, objective, and character
  description — so they match the narrator text.

## Capabilities

### New Capabilities
- `reading-preferences`: player-controlled appearance settings for the narrator
  text (font family incl. a dyslexia-friendly option, text size) plus theme,
  persisted and applied across sessions.

### Modified Capabilities
<!-- none -->

## Impact

- Frontend:
  - `src/app/globals.css` — load Atkinson Hyperlegible; drive `.narrativa` font
    family and size from CSS variables.
  - `src/store/settings-store.ts` (new) — zustand + persist store for font/size.
  - `src/components/settings-sheet.tsx` (new) — the settings UI (font, size,
    theme), reusing `ui/sheet.tsx`.
  - `src/components/header.tsx` — add gear icon to open the sheet; remove the
    standalone theme toggle (now inside the sheet).
  - A small applier (effect/provider) writes the CSS variables onto `<html>`.
- No backend changes.
