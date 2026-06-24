## 1. Tests first (RED)

- [x] 1.1 Add/extend a test for `dice-3d-canvas` asserting `onSettled` is invoked exactly once after the throw completes
- [x] 1.2 Add a test asserting the die still ends oriented on the server `valor` (mock/inspect final quaternion against `quaternionParaValor(valor)`)
- [x] 1.3 Add a test asserting the WebGL-unavailable fallback still calls `onSettled` (animation skipped)

## 2. Trajectory + timing model

- [x] 2.1 Replace `DUR_TUMBLE`/`DUR_SETTLE` with named constants: `DUR_FLIGHT`, `DUR_BOUNCE_1`, `DUR_BOUNCE_2`, `DUR_SETTLE`, restitution `e`, launch offset, camera-far distance, `ω` max
- [x] 2.2 Implement the height function `y(t)`: launch apex → two parabolic bounces with `apex_{n+1} = apex_n * e` → rest at `y = 0`
- [x] 2.3 Implement horizontal `x(t)` easing from off-center launch toward center
- [x] 2.4 Drive `mesh.position` from `x(t)`/`y(t)` each frame across the phases

## 3. Continuous orientation + deterministic landing

- [x] 3.1 Integrate orientation continuously: `q ← q * Δq(ω·dt)` with a randomized tumble axis
- [x] 3.2 Decay `ω` magnitude, stepping it down at each bounce impact
- [x] 3.3 In the final settle window, slerp the live `q` into `objetivo` with an ease reaching 1 at rest (no fixed `desde`, no snap)
- [x] 3.4 Verify the resting orientation equals `quaternionParaValor(valor)` and the rest pose for the idle state stays face-20

## 4. Camera dolly

- [x] 4.1 Animate `camera.position.z` from 4 → ~6–6.5 at peak flight → back to 4 at settle, synced to the arc
- [x] 4.2 Tune the dolly-far distance so the arc apex stays fully within the frame and the resting face is legible

## 5. Landing feedback

- [x] 5.1 Apply a transient squash/stretch (non-uniform scale, eased back over a few frames) on each bounce impact
- [x] 5.2 Keep the critical-result emissive flash on final rest (`exito_critico` / `fracaso_critico`) and fire `onSettled` once when the settle ease completes

## 6. Cleanup, verify, tune

- [x] 6.1 Confirm reduced motion is ignored — the full throw always plays on activation
- [x] 6.2 Ensure three.js resources (geometry, material, textures, renderer) are still disposed on unmount
- [x] 6.3 Run `pnpm typecheck`, `pnpm lint`, and the dice tests; all green
- [x] 6.4 Manually tune restitution `e` and per-phase durations against the live canvas (total ~2–2.5s, in-frame, satisfying bounce)
