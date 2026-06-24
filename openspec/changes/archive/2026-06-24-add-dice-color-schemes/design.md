## Context

The 3D d20 is rendered in `dice-3d-canvas.tsx` with three hardcoded surfaces: the
icosahedron body color (`0xe5e7eb`), the number-label fill (`#111827`), and the
material finish (`metalness: 0.3`, `roughness: 0.4`). A separate per-result emissive
map (`EMISSIVE`) drives the glow that signals the roll outcome (gold/emerald/gray/red).

Appearance preferences (narrator font, narrator text size) already follow an
established pattern: an enum + value map in `settings-store.ts` (zustand + `persist`
to localStorage), a control group in `settings-sheet.tsx`, and consumers reading the
store. Theme is handled separately by next-themes. This change adds a dice color
scheme that reuses that same pattern.

## Goals / Non-Goals

**Goals:**
- Let the player pick from three predefined d20 color schemes (body, numbers, finish).
- Persist the choice locally and apply it on the next dice render.
- Keep the result glow fixed and semantic, independent of the chosen scheme.
- Reuse the existing settings-store / settings-sheet pattern — no new infrastructure.

**Non-Goals:**
- Custom/arbitrary colors or a color picker (fixed presets only).
- Per-game or server-side persistence (local only, like other appearance prefs).
- Live re-render of an in-progress roll when the scheme changes mid-overlay.
- Any change to the result-glow colors or to roll mechanics.

## Decisions

### Schemes as a single source-of-truth palette map

Define `DiceScheme = "marfil" | "obsidiana" | "esmeralda"` and a
`DICE_SCHEMES: Record<DiceScheme, { body: number; label: string; metalness: number; roughness: number }>`
map in `settings-store.ts`, mirroring `FONT_STACKS` / `SIZE_VALUES`. Concrete values:

| Scheme | body | label | metalness | roughness |
|---|---|---|---|---|
| `marfil` (default) | `0xe5e7eb` | `#111827` | 0.3 | 0.4 |
| `obsidiana` | `0x1f2937` | `#f9fafb` | 0.6 | 0.2 |
| `esmeralda` | `0x065f46` | `#d1fae5` | 0.5 | 0.5 |

Body colors are stored as numbers (three.js `THREE.Color` / `MeshStandardMaterial.color`
take hex numbers); label colors as CSS strings (used as the canvas `fillStyle`).
_Alternative considered:_ inlining colors in the component via a `switch`. Rejected —
keeping the palette beside the other preference maps keeps the store the single source
of truth and makes the schemes testable without rendering WebGL.

### Component reads the scheme from the store and threads it through

`texturaNumero(n)` currently hardcodes `ctx.fillStyle = "#111827"`; it takes the label
color as a parameter (`texturaNumero(n, labelColor)`), threaded through
`construirRotulos(labelColor)`. The material uses `scheme.body`, `scheme.metalness`,
`scheme.roughness`. The `EMISSIVE[resultado]` glow and its intensity logic are left
untouched.

### Scheme added to the render useEffect deps

The render effect deps are `[valor, resultado]`. Add `diceScheme` so that if the store
value changes while the canvas is mounted, the scene rebuilds with the new palette.
In practice the overlay is short-lived, but adding the dep makes the behavior correct
rather than incidental. _Alternative considered:_ reading the scheme via a ref to avoid
rebuilds. Rejected — the effect already fully rebuilds the scene on dependency change,
and a full rebuild on a rare scheme switch is cheap and simpler.

## Risks / Trade-offs

- **Low contrast on a future scheme** → The three chosen schemes pair body and label
  for legibility; the spec requires numbers stay readable, and any added scheme must
  satisfy that.
- **Result glow muted on a same-tone body** (e.g. the dim gray failure glow on the
  Obsidiana charcoal body) → Acceptable and intended: a non-critical failure is meant
  to read as "nothing special"; the critical gold/red glows still pop on all bodies.
- **Persisted enum drift** → If a stored scheme value is ever removed, the consumer
  should fall back to the default rather than crash. Keep the default lookup defensive.
