## Why

The d20 animation shipped in `add-d20-skill-checks` plays automatically on a featureless die and auto-dismisses after ~1.6s, while the outcome narration streams into the page behind the modal. Players have no agency over the roll, can't read the result at their own pace, and the narrator text appears before they're done looking at the die. We want the roll to feel like the player throws the die and reads the consequence deliberately.

## What Changes

- The 3D die SHALL render the numbers 1–20 on its faces (the value the die settles on is legible on the die itself, not only in the text reveal).
- The animation SHALL NOT start on its own: the die rests centered showing face 20, and the tumble+settle plays only after the player clicks the die (or its area).
- The dice modal SHALL stay open until the player dismisses it (a close button top-right, or a click outside) — the auto-close timer is removed. **BREAKING** to the current auto-dismiss behavior.
- The outcome narration received over SSE SHALL NOT fill the narrator while the modal is open; it is buffered and revealed only once the player closes the modal. If the modal is closed before phase-2 finishes streaming, the narration continues live from that point; if it already finished, it replays as a typewriter reveal.
- The reduced-motion bypass is removed for this interaction: clicking the die always plays the roll animation, since the click is explicit player intent. **BREAKING** to the current reduced-motion fallback.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `skill-checks`: the "Animated 3D dice roll presentation" requirement changes — numbered faces, player-initiated roll, persistent (manually dismissed) modal, narration deferred until dismissal, and removal of the reduced-motion bypass in favor of always animating on click.

## Impact

- Frontend only; **no backend changes**. The SSE event order (`token` phase 1 → `tirada` → `token` phase 2 → `turno` → optional `imagen` → `done`) and payloads are already sufficient.
- Affected code:
  - `frontend/src/components/dice-3d-canvas.tsx` — numbered faces, idle/rolling/settled state machine, click gesture, idle pose on face 20.
  - `frontend/src/lib/d20-geometry.ts` — expose per-face centroid/normal (and roll) for label placement.
  - `frontend/src/components/dice-overlay.tsx` — remove auto-close, add close button, always mount the canvas.
  - `frontend/src/store/partida-store.ts` — buffer the resolved turn (`turnoPendiente`) and flush on modal close.
  - `frontend/src/app/page.tsx` — hide the streaming narration while the dice modal is open.
  - `frontend/src/components/acciones.tsx` — fold final-state and image into the buffered payload.
  - Tests: `frontend/src/components/dice-overlay.test.tsx` (auto-close and reduced-motion bypass tests are replaced).
- Accessibility note: removing the reduced-motion bypass means motion-sensitive players no longer have an automatic escape; an in-game "skip animation" valve is out of scope for this change.
