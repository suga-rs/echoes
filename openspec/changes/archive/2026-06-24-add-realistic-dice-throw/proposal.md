## Why

The d20 roll currently spins in place on its own axes and then cuts to the result face — it reads like a fidget spinner, not a thrown die. The "settle" phase even teleports the die from wherever the tumble left it to a fixed pose before easing to the target, so there is a visible snap instead of a continuous deceleration. Players asked for the die to look like it is actually *thrown* and *lands* on the result.

## What Changes

- Replace the in-place axis spin with a **scripted thrown-arc animation**: the die launches into frame, travels along a parabolic arc, tumbles in flight, **bounces twice** with decaying energy, and comes to rest aligned to the server-rolled face.
- The animation MUST stay **deterministic by construction** — it always settles exactly on the server's value. It is not a physics simulation; the arc and spin are scripted/eased so the landing face is guaranteed.
- Fix the **tumble→settle discontinuity**: orientation is integrated continuously and decelerates into the target face, with no snap to an intermediate pose.
- To fit the big arc inside the small canvas, the **camera dollies back** during flight (die appears thrown from a distance) and dollies in as it settles.
- Add **landing feedback**: a squash/stretch on each impact and the existing critical-result emissive flash on final rest.
- Reduced motion is **explicitly ignored** for this interaction — activating the die always plays the full thrown-arc animation. (Consistent with the prior decision in `refine-d20-dice-interaction`.)

## Capabilities

### New Capabilities
- `dice-throw-animation`: the physical choreography of the d20 roll — thrown-arc trajectory, in-flight tumble, decaying bounces, camera dolly, continuous deceleration, and a guaranteed deterministic landing on the server-rolled face. Layers on top of the roll-presentation behavior owned by `skill-checks` (player-initiated activation, authoritative server result, staged reveal) without changing it.

### Modified Capabilities
<!-- none — the skill-checks roll-presentation requirement (player activation, authoritative result, staged reveal, numbered faces) is unchanged; only the choreography is added. -->

## Impact

- **Frontend only; no backend changes.** The server result and SSE event flow are unchanged.
- Affected code:
  - `frontend/src/components/dice-3d-canvas.tsx` — replace the tumble/settle loop with the launch → flight → bounce → settle state machine; add camera dolly and per-impact squash/stretch; integrate orientation continuously and decelerate into the target quaternion.
  - `frontend/src/lib/d20-geometry.ts` — reused as-is for the target/rest quaternions; may add a small easing/trajectory helper if it keeps the canvas component readable.
  - Tests: `frontend/src/components/dice-3d-canvas.test.tsx` (or equivalent) — assert the die still ends on the server value and `onSettled` fires once.
- No new runtime dependencies (no physics engine) — everything is built on the existing `three` setup.
