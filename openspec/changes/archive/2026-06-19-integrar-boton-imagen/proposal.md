## Why

When a turn has no image, the on-demand "Generar imagen" control renders as a
lone outline button floating in the collapsed image slot. Because only the first
and last turns auto-generate images, most turns show this button, so the empty
slot + stray button reads as unfinished and out of place.

## What Changes

- Move the on-demand image control out of the empty image slot and into the
  turn card's header row, beside the existing "Incoherente" flag, as a subtle
  icon-button with a tooltip.
- Remove the empty placeholder area that previously held the button, so
  image-less turns no longer show a gap.
- Preserve current behavior: clicking generates the image, the loading skeleton
  appears in the image area while generating, errors and the "limit reached"
  message still surface.

## Capabilities

### New Capabilities
- `turn-image-affordance`: how the player requests an on-demand image for a turn
  and where that control lives in the turn card.

### Modified Capabilities
<!-- none -->

## Impact

- Frontend only:
  - `src/components/turno-card.tsx` — relocate the generate control to the header
    row; keep the generating skeleton, error text, and limit-reached handling.
- No backend or API changes; `api.generarImagenTurno` is unchanged.
