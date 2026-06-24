## 1. Settings store: scheme model + persistence

- [x] 1.1 Add a failing test in `frontend/src/store/settings-store.test.ts` (or sibling) asserting the store defaults `diceScheme` to `"marfil"` and that `setDiceScheme` updates it
- [x] 1.2 In `frontend/src/store/settings-store.ts`, add `export type DiceScheme = "marfil" | "obsidiana" | "esmeralda"`
- [x] 1.3 Add `export const DICE_SCHEMES: Record<DiceScheme, { body: number; label: string; metalness: number; roughness: number }>` with the values from design.md (marfil `0xe5e7eb`/`#111827`/0.3/0.4, obsidiana `0x1f2937`/`#f9fafb`/0.6/0.2, esmeralda `0x065f46`/`#d1fae5`/0.5/0.5)
- [x] 1.4 Add `diceScheme` state (default `"marfil"`) and `setDiceScheme` setter to the persisted store
- [x] 1.5 Run the store test green

## 2. Settings sheet: dice color control

- [x] 2.1 Add/extend a failing test in `frontend/src/components/settings-sheet.test.tsx` asserting a "Color del dado" option group renders three options and selecting one calls `setDiceScheme`
- [x] 2.2 In `frontend/src/components/settings-sheet.tsx`, add `DICE_SCHEME_OPTIONS` (`marfil`→"Marfil", `obsidiana`→"Obsidiana", `esmeralda`→"Esmeralda") and a new `<OptionGroup label="Color del dado" ...>` wired to `diceScheme` / `setDiceScheme`
- [x] 2.3 Run the settings-sheet test green

## 3. Dice canvas: apply the scheme

- [x] 3.1 In `frontend/src/components/dice-3d-canvas.tsx`, read `diceScheme` from the settings store and resolve its palette via `DICE_SCHEMES` (defensive fallback to `marfil` if missing)
- [x] 3.2 Parameterize `texturaNumero(n, labelColor)` and `construirRotulos(labelColor)` to use the scheme's label color instead of the hardcoded `#111827`
- [x] 3.3 Use the scheme's `body`, `metalness`, and `roughness` for the `MeshStandardMaterial`; leave the `EMISSIVE[resultado]` glow and intensity logic untouched
- [x] 3.4 Add `diceScheme` to the render `useEffect` dependency array

## 4. Verification

- [x] 4.1 Run `pnpm typecheck` and `pnpm lint` clean
- [x] 4.2 Run `pnpm test` — all suites green
- [ ] 4.3 Manually verify in the app: each scheme changes body/number/finish, numbers stay legible, the result glow (crit gold / success emerald / fail gray / crit-fail red) is unchanged across schemes, and the choice survives a reload
