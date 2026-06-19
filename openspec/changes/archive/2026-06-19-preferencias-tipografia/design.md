## Context

The narrator text is styled by the `.narrativa` class in `src/app/globals.css`,
hardcoded to `font-family: theme("fontFamily.serif")` (Crimson Text) at
`font-size: 1.05rem`. Fonts are loaded with a Google Fonts `@import` at the top of
`globals.css`. Theme is handled by `next-themes` (`ThemeProvider` in
`providers.tsx`) with a `ThemeToggle` button in the header. There is no general
settings store; `auth-store.ts` is the established pattern for a persisted zustand
store. The header already carries ~9 controls.

## Goals / Non-Goals

**Goals:**
- A single settings panel (slide-over sheet) for appearance.
- Player-selectable narrator font: serif (default), sans, dyslexia-friendly.
- Player-selectable narrator size: small / medium / large.
- Persist preferences and apply them live and on reload.
- Consolidate theme into the settings panel; remove the standalone header toggle.

**Goals (extended):**
- Apply the chosen narrator **font family** (not size) to the other narrative
  game-text surfaces — player actions, option buttons, inventory, objective,
  character description — so they match the narrator.

**Non-Goals:**
- Applying the narrator **size** preference to anything beyond the narrator text.
- Making chrome/UI typography (buttons in general, dialog chrome, header labels)
  configurable — only the narrative game-text surfaces share the font.
- Server-side persistence / syncing preferences to the user account.
- A full theming system (custom colors, line spacing, etc.) — only font + size
  (+ existing theme) for now.
- Switching the whole app font; only the narrator text is configurable.

## Decisions

### Dyslexia font: Atkinson Hyperlegible via Google Fonts

Chosen over OpenDyslexic because it is available on Google Fonts and ships with
the same one-line `@import` already used for Crimson Text + Inter — no self-hosted
font files or `next/font/local` wiring. It is broadly legible for low-vision
readers. Trade-off: it is less "recognizable" as the canonical dyslexia font than
OpenDyslexic; accepted for the simpler delivery. Self-hosting OpenDyslexic remains
a future option if requested.

### Apply via CSS variables on `<html>`, not Tailwind classes

`.narrativa` becomes `font-family: var(--font-narrativa); font-size:
var(--narrativa-size)`. The settings store maps its enum values to concrete
font-family stacks and rem sizes and writes them as inline custom properties on
`document.documentElement`. Rationale: the narrator text is rendered in many
places (turno-card, streaming card); a single source of truth via CSS vars avoids
threading props through components and keeps the change localized to CSS + one
applier. Defaults live in `:root` so the unconfigured state matches today's look.

### Font-only sharing via a second class `.fuente-narrativa`

The narrator keeps `.narrativa` (font-family + font-size + line-height). A second
class — `.fuente-narrativa` — sets **only** `font-family: var(--font-narrativa)`
and is applied to the player-action bubble (`turno-card`), the option buttons
(`acciones`), the inventory items, the objective, and the character description
(`header`). It reuses the existing `--font-narrativa` variable, so no new store
field or applier wiring is needed. Size is deliberately omitted to avoid breaking
the header/button layout at the `lg` size; only the narrator text resizes.

### State: a persisted zustand store mirroring `auth-store`

New `settings-store.ts` with `narrativaFont: 'serif' | 'sans' | 'dyslexic'` and
`narrativaSize: 'sm' | 'md' | 'lg'`, persisted under a key like
`aventuras-settings`. Theme stays owned by `next-themes` (don't reinvent it); the
settings sheet simply renders theme controls using `useTheme()`. This avoids two
competing sources of truth for theme.

### Avoiding the default-value flash on reload

zustand `persist` hydrates on the client after mount, so a naive applier would
briefly show defaults. Mitigation: write the CSS variables from the persisted
value as early as possible — an applier effect that runs on mount, and/or a tiny
inline script in the layout `<head>` that reads `localStorage` and sets the
variables before paint (same approach `next-themes` uses for theme). The spec's
"applied without flashing the default" scenario is satisfied by the pre-paint set.

### Settings as a Sheet, opened by a gear icon

Reuse `src/components/ui/sheet.tsx` (already used by the partidas sidebar). A gear
icon button is added to the header; the standalone `ThemeToggle` is removed from
the header and its theme control relocated into the sheet, keeping the header
control count flat.

## Risks / Trade-offs

- [Flash of default styling on load] → Mitigate with a pre-paint inline script
  reading localStorage, mirroring next-themes; otherwise an early mount effect.
- [Atkinson less recognizable than OpenDyslexic] → Accepted for simpler delivery;
  OpenDyslexic can be added later via self-hosting if requested.
- [Extra Google Font weight on every load] → One additional family; acceptable,
  loaded the same way as the existing two.
- [Theme ownership split feels like two systems] → Keep theme in next-themes and
  only surface its control in the sheet; settings store owns font/size only.

## Open Questions

- Size control shape: discrete sm/md/lg buttons (chosen, simplest) vs. a slider.
  Defaulting to discrete buttons.
- Exact rem values for sm/md/lg (e.g. 0.95 / 1.05 / 1.2 rem) — finalized at
  implementation against the current 1.05rem baseline (md).
