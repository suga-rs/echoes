## 1. Fonts & CSS

- [x] 1.1 Add Atkinson Hyperlegible to the Google Fonts `@import` in `src/app/globals.css`.
- [x] 1.2 Define default CSS variables `--font-narrativa` and `--narrativa-size` in `:root` matching the current look (serif stack, 1.05rem).
- [x] 1.3 Update `.narrativa` to use `font-family: var(--font-narrativa)` and `font-size: var(--narrativa-size)`.

## 2. Settings store & applier

- [x] 2.1 Write failing tests for `settings-store` (defaults serif/md; setters update state; persistence key).
- [x] 2.2 Create `src/store/settings-store.ts` (zustand + persist, key `aventuras-settings`) with `narrativaFont` and `narrativaSize` + setters. Make tests pass.
- [x] 2.3 Add an applier that maps store values to font stacks / rem sizes and writes `--font-narrativa` and `--narrativa-size` on `document.documentElement` (mount effect).
- [x] 2.4 Add a pre-paint inline script in `src/app/layout.tsx` (mirroring next-themes) that reads the persisted preference from localStorage and sets the CSS variables before first paint, to avoid a default-value flash.

## 3. Settings sheet UI

- [x] 3.1 Create `src/components/settings-sheet.tsx` using `ui/sheet.tsx`, with a narrator-font selector (serif/sans/dyslexic), a size selector (sm/md/lg), and the theme control (via `useTheme()`).
- [x] 3.2 Add a gear icon button to `src/components/header.tsx` that opens the settings sheet.
- [x] 3.3 Remove the standalone `ThemeToggle` from the header (theme now lives in the sheet).

## 4. Tests & verification

- [x] 4.1 Component test: changing font/size updates the CSS variables / store; reload reflects persisted values.
- [x] 4.2 Run `pnpm lint`, `pnpm typecheck`, and frontend tests; fix issues.
- [ ] 4.3 Manually verify each font (incl. dyslexia option) and each size render in the narrator text, in light and dark theme.

## 5. Extend font to game-text surfaces

- [x] 5.1 Add a `.fuente-narrativa` class in `src/app/globals.css` that sets only `font-family: var(--font-narrativa)` (no size, no line-height).
- [x] 5.2 Apply `.fuente-narrativa` to the player-action bubble in `src/components/turno-card.tsx`.
- [x] 5.3 Apply `.fuente-narrativa` to the option buttons in `src/components/acciones.tsx`.
- [x] 5.4 Apply `.fuente-narrativa` to the inventory items, objective, and character description in `src/components/header.tsx`.
- [x] 5.5 Add/extend a component test asserting the chosen font applies to a game-text surface and that the size preference does not resize it.
- [x] 5.6 Run `pnpm lint`, `pnpm typecheck`, and frontend tests; manually verify the font matches across all five surfaces (automated checks pass; visual verification pending).
