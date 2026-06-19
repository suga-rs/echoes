## Context

`src/components/turno-card.tsx` renders, for a turn without an image, a centered
`<Button variant="outline">Generar imagen</Button>` inside a `mb-4 flex flex-col`
block that sits in the otherwise-empty image slot (lines ~93–108). The card header
row (lines ~111–126) already holds the "Turno N" label and the "Incoherente" flag
button. The generating state shows an `aspect-[3/2] animate-pulse` skeleton; the
component also tracks `error` and `limiteAlcanzado`. Only the first and last turns
auto-generate images, so most turns render the stray button.

This change is small and purely presentational — no API, store, or backend impact.

## Goals / Non-Goals

**Goals:**
- Relocate the generate control into the header row beside the Incoherente flag.
- Eliminate the empty placeholder block for image-less turns.
- Keep the generating skeleton, error text, and limit-reached message behavior.

**Non-Goals:**
- Changing image generation logic, the API, or the image budget.
- Changing how existing images render or the image modal.
- Redesigning the header beyond adding this one control.

## Decisions

### Compact icon-button in the header, with tooltip

The control becomes a small icon-button (reuse the `ImagePlus` icon) placed in the
existing header `flex items-center justify-between` row, grouped with the
Incoherente flag. Because an icon alone is less discoverable than the old text
button, it carries an accessible label and a `title`/tooltip ("Ilustrar esta
escena"). Chosen over the alternatives (full dropzone, short dashed band) for
minimal footprint and zero layout cost on every image-less turn.

### Skeleton stays in the image area

While generating (`generando` or `imagenCargando`), the existing
`aspect-[3/2] animate-pulse` skeleton continues to occupy the image area, giving
clear feedback that an image is incoming. Only the idle "no image yet" state loses
its placeholder block — when idle and image-less, nothing renders above the
narrative except the card itself.

### Error and limit-reached placement

`error` text and the `limiteAlcanzado` message move with the control. When the cap
is reached, the header control is hidden/disabled and the limit message is shown
(small, in the header or just above the narrative) rather than the old centered
text. Behavior is preserved; only placement changes.

## Risks / Trade-offs

- [Lower discoverability of an icon vs. a labeled button] → Mitigate with a
  tooltip/accessible label; the icon sits next to the familiar Incoherente flag.
- [Header row crowding on small screens] → Two compact controls in the header row;
  keep them icon-sized and verify wrapping on narrow widths.
