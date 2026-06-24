## Context

The d20 roll lives entirely in [dice-3d-canvas.tsx](../../../frontend/src/components/dice-3d-canvas.tsx) using plain `three.js` (no react-three-fiber). The current loop has three states: a `reposo` pose (face 20 toward camera), a `DUR_TUMBLE` phase that increments `mesh.rotation` on x/y/z in place, and a `DUR_SETTLE` phase that slerps from a fixed `desde` Euler pose to `objetivo` (the target quaternion from `quaternionParaValor(valor)`).

Two structural problems drive this change:

1. **No translation** — the die's center never leaves the origin, so it spins like a top instead of being thrown.
2. **A snap, not a deceleration** — the tumble accumulates Euler rotation, but the settle ignores where the tumble ended and starts from the fixed `desde` pose, producing a visible teleport at `t = DUR_TUMBLE`.

The authoritative result is the server's `valor`; the animation is realce only. The canvas is small (~192px) and the die nearly fills it: camera fov 45° at z=4 gives ~1.66 units of visible half-height while the die spans ~±1.3, leaving only ~0.35 units of headroom. A big arc cannot fit at a fixed camera distance.

## Goals / Non-Goals

**Goals:**
- A thrown-die feel: launch, parabolic arc, in-flight tumble, two decaying bounces, settle on the result face.
- Guaranteed deterministic landing on the server value, with no new dependencies.
- Continuous orientation — remove the tumble→settle snap.
- Keep the die in frame via a camera dolly tied to the throw timeline.

**Non-Goals:**
- Real rigid-body physics (cannon-es / rapier). Excluded — cannot guarantee the server face and adds bundle weight.
- Changing the roll-presentation contract owned by `skill-checks` (player activation, authoritative result, staged reveal, numbered faces, persistent modal).
- A reduced-motion / skip valve — explicitly out of scope; the throw always plays.

## Decisions

### Decision: Scripted keyframed throw, not physics

The trajectory (position arc + bounces) and the spin are driven by eased time functions, and the **final** orientation is forced to `objetivo` by slerping the live orientation into it during the settle window. This makes the landing face guaranteed by construction.

*Alternative considered — rapier/cannon physics:* most physical, but the resting face is emergent and would not match the server roll without an unnatural post-hoc snap, plus a sizeable dependency. Rejected.

### Decision: Position model — parabolic arc + two decaying bounces

A single height function `y(t)` over the throw drives vertical position; horizontal `x(t)` eases from an off-center launch toward center. Bounces are modeled as successive parabolas with a restitution factor (`apex_{n+1} = apex_n * e`, `e ≈ 0.45`) so each bounce is visibly lower, terminating at `y = 0` at rest.

```
phases (normalized t):
 LAUNCH→FLIGHT   BOUNCE 1     BOUNCE 2    SETTLE
 y: high apex ──▶ ╱╲ apex·e ─▶ ╱╲ apex·e² ─▶ y=0
 spin: fast ωmax ───── decays per impact ─────▶ ω→0
 align: free tumble ─────────────▶ blend into objetivo
```

### Decision: Continuous orientation via closed-form tumble + late alignment, in a pure module

The throw math (position, orientation, camera-z, impact scale, all as functions of elapsed `t`) is extracted into a **pure, closed-form module** (`frontend/src/lib/dice-throw.ts`) separate from the three.js rendering in the canvas component. This makes it frame-rate independent and unit-testable without a WebGL context (jsdom has none).

Orientation is a closed form, not frame-integrated: during flight `q(t) = qInicial · axisAngle(tumbleAxis, θ(t))` where `θ(t)` is the integral of a decaying angular speed (stepped down at each bounce) — closed form, so deterministic and reproducible. During the final settle window, `q(t) = slerp(qSettleStart, objetivo, ease(...))` where `qSettleStart` is the flight orientation evaluated at the settle boundary. Because both branches agree at the boundary (`qSettleStart`) and the settle ease reaches 1 exactly at `t = TOTAL`, the orientation is continuous (no snap) **and** lands exactly on `objetivo` by construction. `quaternionParaValor` / `quaternionParaValor(20)` stay the source of truth for target and rest poses.

*Alternative considered — per-frame `q ← q · Δq(ω·dt)` integration:* frame-rate dependent and not unit-testable without rendering. Rejected for the closed form.
*Alternative considered — keep fixed `desde` and just shorten it:* still snaps. Rejected.

### Decision: Camera dolly instead of scaling the die

Animate `camera.position.z` from 4 (rest) out to ~6–6.5 at peak flight and back to 4 at settle, synced to the arc. Pulling the camera keeps the die's apparent size small mid-flight (room for the arc) and large at rest (legible face), and avoids re-tuning label offsets that a mesh scale would disturb.

*Alternative considered — scale the mesh down in flight:* interacts with label plane offsets and lighting; dolly is cleaner.

### Decision: Squash/stretch on impact via transient non-uniform scale

At each bounce impact, briefly scale the mesh (e.g. flatten on the impact axis, ~0.85/1.15) and ease back over a few frames. Cheap, no geometry changes, sells the impact. Critical-result emissive flash stays as-is on final rest, and `onSettled` fires once when the settle ease completes.

### Decision: Tunable timing constants

Replace `DUR_TUMBLE` / `DUR_SETTLE` with a small set of named constants: `DUR_FLIGHT`, `DUR_BOUNCE_1`, `DUR_BOUNCE_2`, `DUR_SETTLE`, restitution `e`, launch offset, camera-far distance, and `ω` max. Keeping them grouped and named makes the feel tunable without restructuring the loop.

## Risks / Trade-offs

- **Arc clips the frame** → camera dolly is tuned against the ~0.35-unit headroom budget; the spec requires the die stays fully visible, so the dolly-far distance is chosen so the apex fits.
- **Alignment looks "magnetized" if it starts too early** → confine the slerp-to-target to the final settle window after the last bounce, so the visible alignment coincides with the die slowing naturally.
- **Total duration grows** (flight + 2 bounces + settle vs. ~1.9s today) → keep the sum in a comfortable ~2–2.5s range; the modal no longer auto-dismisses, so a slightly longer roll is acceptable.
- **Determinism vs. randomness** → randomize only the in-flight tumble axis and minor arc jitter; never the final pose, which is always `objetivo`.
- **Reduced-motion accessibility** → intentionally unaddressed per the proposal; a skip valve remains out of scope.

## Open Questions

- Exact restitution `e` and per-phase durations are feel-driven and will be tuned during implementation against the live canvas; the spec fixes the qualitative behavior (two decaying bounces, in-frame, legible rest), not the numbers.
