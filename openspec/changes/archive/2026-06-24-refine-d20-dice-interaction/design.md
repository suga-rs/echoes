## Context

The d20 presentation from `add-d20-skill-checks` is split across:

- `dice-3d-canvas.tsx` — vanilla three.js icosahedron that tumbles and slerps to `quaternionParaValor(valor)` on mount, then calls `onSettled`.
- `d20-geometry.ts` — deterministic value→face-index→quaternion lookup (value `v` ↔ face index `v-1`).
- `dice-overlay.tsx` — Radix dialog; under reduced-motion it skips the canvas and reveals immediately; otherwise it animates and auto-closes ~1.6s after settle. The default close button is hidden (`[&>button]:hidden`).
- `partida-store.ts` — `iniciarTirada` opens the overlay and resets `streamingNarrativa`; `finalizarStreaming` commits the turn to `historial`, clears the stream, and sets `tiradaActual=null` (which closes the overlay).
- `acciones.tsx` — SSE handler: `onTirada→iniciarTirada`, phase-2 `onToken→appendStreamToken`, `onTurno→finalizarStreaming` (+ `actualizarEstadoFinal`), `onImagen→actualizarImagenTurno`.
- `page.tsx` — renders `StreamingTurnoCard` whenever `isStreaming && streamingNarrativa!==null`, and mounts `DiceOverlay` whenever `tiradaActual`.

SSE event order for a checked turn is fixed and cannot be paused: `token`(phase 1) → `tirada` → `token`(phase 2) → `turno` → optional `imagen` → `done`. The backend is authoritative and unchanged.

The current coupling means phase-2 narration streams into the page *behind* the open modal, and `finalizarStreaming` both commits the narration and closes the modal. The four requested behaviors break that coupling.

## Goals / Non-Goals

**Goals:**
- Numbers 1–20 legible on the die's faces, consistent with the existing value→face mapping.
- Player-initiated roll: die idles on face 20, animates only on click.
- Modal persists until the player dismisses it (close control or click outside); no auto-dismiss.
- Narration is withheld from the narrator until the modal is dismissed; replay-typewriter if already arrived, live continuation if dismissed mid-stream.
- Clicking always animates, including under reduced motion.

**Non-Goals:**
- No backend changes; SSE contract is untouched.
- No in-game "skip animation" accessibility valve (called out as a follow-up).
- No change to roll resolution, DC mapping, result tiers, or the static `TiradaReveal` content.
- No real-d20 face numbering layout (opposite faces summing to 21); the existing internal `v ↔ v-1` mapping is kept.

## Decisions

### 1. Face numbers via per-face textured planes parented to the die mesh

Render 20 small planes, each with a `CanvasTexture` of one number, positioned at the corresponding face centroid and oriented along the face normal, parented to the die mesh so they tumble with it. `d20-geometry.ts` gains an exported `caras()` (or `centroideYNormalDeCara(i)`) helper reusing its existing geometry/normal math; face index `i` is labelled `i+1`, matching `quaternionParaValor`.

- **Alternative — billboard sprites:** always face the camera, so all 20 numbers stay readable including the back faces, destroying the 3D illusion. Rejected.
- **Alternative — UV-mapped texture atlas on the icosahedron:** most authentic but requires UVing a 60-vertex non-indexed geometry; high effort for marginal gain. Deferred.
- **In-plane roll caveat:** `setFromUnitVectors(normal, +Z)` fixes the face normal but leaves an arbitrary in-plane rotation, so the settled number may read slightly rotated. Acceptable for a tumbling die; if "20 perfectly upright" is desired, add a per-face roll correction to the idle pose (face 20) and the settle target. Treated as optional polish.

### 2. Idle/rolling/settled state machine, click-gated, in the canvas

The canvas keeps the render loop but starts in `idle`: `mesh.quaternion = quaternionParaValor(20)`, numbers visible, no tumble. A pointer handler on the canvas/container transitions `idle→rolling`, which runs the existing tumble+settle to `valor` and on completion enters `settled` (applies the critical glow and calls `onSettled`). The `desde`/`objetivo` quaternion logic is unchanged; only its trigger moves from mount to the click.

- The reduced-motion bypass is removed: the canvas always mounts and the click always animates (per the resolved requirement). This collapses two render paths into one.

### 3. Modal persistence: drop the timer, show a close control

Remove the `setTimeout(onClose, …)` effect in `dice-overlay.tsx`. Stop hiding the Radix close button (drop `[&>button]:hidden`) or add an explicit top-right close control. `onOpenChange(false)→onClose` already covers click-outside/Esc. `onClose` maps to `cerrarTirada`.

### 4. Buffer the resolved turn; flush on modal close (store-centric)

The store becomes the coordination point because `acciones.tsx` doesn't observe when the modal closes. Introduce `turnoPendiente` holding the full resolved-turn payload (turno fields + `imagenPendiente` + final-state).

- `finalizarStreaming`: if `tiradaActual !== null`, stash the payload in `turnoPendiente` and DO NOT touch `historial`, `streamingNarrativa`, or `tiradaActual`. Otherwise behave as today (direct commit). This stops the modal from auto-closing and stops the narrator from filling while open.
- `cerrarTirada`: set `tiradaActual=null`, then flush:
  - if `turnoPendiente` exists → SSE finished: clear `streamingNarrativa` and drive a **typewriter replay** of `turnoPendiente.narrativa`, then commit to `historial` (+ apply final-state + buffered image URL).
  - if `turnoPendiente` is null → dismissed early: leave `streamingNarrativa` as-is so `StreamingTurnoCard` resumes live; the later `onTurno` arrives with `tiradaActual` already null and commits via the normal path.
- Final-state and image are folded into the buffered payload so `actualizarEstadoFinal`/`actualizarImagenTurno` don't fire against a turn that isn't in `historial` yet. `onImagen` (final turns only) writes into `turnoPendiente` while it exists; applied on flush.
- `page.tsx`: render `StreamingTurnoCard` only when `tiradaActual === null`, hiding phase-2 tokens behind the modal regardless of the branch above.

Typewriter replay: clear `streamingNarrativa` on flush and re-feed `turnoPendiente.narrativa` in chunks via `appendStreamToken` on a timer/raf, then call the existing commit. This reuses `StreamingTurnoCard` for the reveal with zero new view component.

- **Alternative — commit immediately but hide the last turn while modal open:** requires a "hidden/blurred" mode on `TurnoCard` and `Acciones`; messier than not committing. Rejected.
- **Alternative — coordinate via a flag watched in `acciones.tsx`:** brittle ordering and effect soup; the store already owns the shared state. Rejected.

## Risks / Trade-offs

- [Reduced-motion players lose the automatic escape] → Intentional per the resolved requirement; documented as out of scope. Mitigation deferred to a possible in-game "skip animation" preference.
- [Number planes add 20 meshes + 20 canvas textures per roll] → Small count and disposed on unmount alongside geometry/material; reuse a single shared texture set if profiling shows cost.
- [Settled number may read rotated due to arbitrary in-plane roll] → Acceptable; optional per-face roll correction available if needed.
- [Image event arrives while turno is buffered (final turns)] → Buffer the URL on `turnoPendiente` and apply on flush; covered by the buffering design.
- [User closes modal between `turno` and a not-yet-applied image on a final turn] → Flush commits the turn; the image, if it arrives after close, applies via the normal `actualizarImagenTurno` once the turn is in `historial`.
- [Existing tests assert auto-close and reduced-motion bypass] → `dice-overlay.test.tsx` is rewritten for the new behavior; this is expected churn, not a regression.

## Migration Plan

Frontend-only, no data or API migration. Ships as one PR. Rollback is reverting the PR; no persisted state shape changes (`turnoPendiente` is in-memory store state only, not persisted — `partialize` still persists only `codigoPartida`).

## Open Questions

- Should "20 upright" be enforced via per-face roll correction, or is the natural tumble orientation acceptable? (Polish; default: accept natural orientation.)
- Do we want a future "skip animation" / reduced-motion accessibility valve? (Out of scope here.)
