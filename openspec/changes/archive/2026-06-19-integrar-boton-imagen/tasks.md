## 1. Relocate the control

- [x] 1.1 In `src/components/turno-card.tsx`, add a compact image icon-button (`ImagePlus`) to the header row beside the Incoherente flag, with an accessible label and `title` tooltip ("Ilustrar esta escena"); wire it to the existing `generarImagen` handler.
- [x] 1.2 Render the header control only when the turn has no image and is not currently generating; hide/disable it when `limiteAlcanzado`.
- [x] 1.3 Remove the old centered placeholder block (the `flex flex-col` "Generar imagen" area) from the image slot.

## 2. Preserve feedback states

- [x] 2.1 Keep the `aspect-[3/2] animate-pulse` skeleton while `generando || imagenCargando`.
- [x] 2.2 Relocate the `error` text and the `limiteAlcanzado` message to display near the header control (preserve current copy/behavior).

## 3. Tests & verification

- [x] 3.1 Update/extend `src/components/turno-card.test.tsx`: control appears in header for image-less turns, hidden when an image exists; generating shows skeleton; error and limit-reached states render.
- [x] 3.2 Run `pnpm lint`, `pnpm typecheck`, and frontend tests; fix issues.
- [x] 3.3 Manually verify header layout on narrow widths (no awkward wrapping) in light and dark theme.
