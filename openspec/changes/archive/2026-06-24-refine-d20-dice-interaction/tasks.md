## 1. Geometry helpers for face labels

- [x] 1.1 In `d20-geometry.ts`, export a helper returning per-face centroid and normal (e.g. `caras(): {indice, centroide, normal}[]` or `centroideYNormalDeCara(i)`), reusing the existing geometry/normal math.
- [x] 1.2 Document the labelling contract: face index `i` ↔ value `i+1`, matching `quaternionParaValor`.
- [x] 1.3 Extend `d20-geometry.test.ts`: assert each face's centroid is unit-ish and that the labelled value for the camera-facing face after `quaternionParaValor(v)` is `v`.

## 2. Numbered faces on the 3D die

- [x] 2.1 Generate a `CanvasTexture` per number 1–20 (small canvas with the digit) in `dice-3d-canvas.tsx`.
- [x] 2.2 Add 20 textured planes positioned at each face centroid, oriented along the face normal, parented to the die mesh so they tumble with it.
- [x] 2.3 Dispose the per-face textures/planes on unmount alongside geometry/material.
- [ ] 2.4 (Optional polish) Add a per-face in-plane roll correction so the settled/idle number reads upright.

## 3. Player-initiated roll state machine

- [x] 3.1 Start the canvas in an `idle` state: set `mesh.quaternion = quaternionParaValor(20)`, numbers visible, no tumble.
- [x] 3.2 Add a pointer/click handler on the canvas container that transitions `idle → rolling`.
- [x] 3.3 On `rolling`, run the existing tumble + slerp-to-`valor`; on completion enter `settled`, apply the critical glow, and call `onSettled`.
- [x] 3.4 Ensure the click always animates (no reduced-motion short-circuit in the canvas).
- [x] 3.5 Add an affordance/cue that the die is clickable (cursor + hint text).

## 4. Persistent modal

- [x] 4.1 Remove the auto-close `setTimeout` effect in `dice-overlay.tsx`.
- [x] 4.2 Always mount the canvas (remove the reduced-motion bypass branch); reveal `TiradaReveal` on `onSettled`.
- [x] 4.3 Show a close control top-right (remove `[&>button]:hidden` or add an explicit button); keep click-outside/Esc → `onClose`.
- [x] 4.4 Keep the static `TiradaReveal` fallback for when the canvas fails to load.

## 5. Buffer the resolved turn in the store

- [x] 5.1 Add `turnoPendiente` state to `partida-store.ts` holding the resolved-turn payload (turno fields + `imagenPendiente` + final-state); not persisted.
- [x] 5.2 Change `finalizarStreaming`: if `tiradaActual !== null`, stash into `turnoPendiente` without touching `historial`/`streamingNarrativa`/`tiradaActual`; else commit as today.
- [x] 5.3 Change `cerrarTirada` to flush: set `tiradaActual=null`; if `turnoPendiente` exists, clear `streamingNarrativa`, typewriter-replay `turnoPendiente.narrativa`, then commit (history + final-state + buffered image); if null, leave `streamingNarrativa` for live continuation.
- [x] 5.4 Fold final-state and image handling into the buffered payload so `actualizarEstadoFinal`/`actualizarImagenTurno` don't target a turn missing from `historial`.
- [x] 5.5 Reset `turnoPendiente` in `resetear` and `cancelarStreaming`.

## 6. Wire the SSE handler and page

- [x] 6.1 In `acciones.tsx`, pass final-state and image into the buffered payload path (via `finalizarStreaming` / store) instead of separate calls when a tirada is active.
- [x] 6.2 In `page.tsx`, render `StreamingTurnoCard` only when `tiradaActual === null` so phase-2 tokens stay hidden behind the modal.
- [x] 6.3 Implement the typewriter-replay mechanism (chunked `appendStreamToken` re-feed of buffered narration) used by `cerrarTirada`.

## 7. Tests and verification

- [x] 7.1 Rewrite `dice-overlay.test.tsx`: remove auto-close and reduced-motion-bypass tests; add tests for "does not animate until click" and "modal stays open until close control / outside click".
- [x] 7.2 Add store tests: buffering on `finalizarStreaming` while `tiradaActual` set; flush + commit on `cerrarTirada` (both replay and live-continuation branches); final-state + image applied on flush.
- [x] 7.3 Add a test that `StreamingTurnoCard` is not shown while `tiradaActual` is set.
- [x] 7.4 Run `pnpm lint`, `pnpm typecheck`, and the frontend test suite; fix fallout.
- [x] 7.5 Manual check: roll, read, dismiss; verify narrator fills only on dismissal (replay) and live-continues when dismissed mid-stream.
