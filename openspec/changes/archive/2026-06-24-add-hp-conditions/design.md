## Context

Milestone 1 (`add-d20-skill-checks`, archived) introduced real, server-rolled d20 skill checks plus a six-attribute character sheet, but deliberately kept failure **purely narrative** — `fracaso`/`fracaso_critico` produce no carried-forward cost. This change is Milestone 2: it gives the existing dice teeth by turning failure into a mechanical consequence (hit points lost, conditions that bias the next roll).

In the layered vision tree, HP/conditions is the **sibling** of the dice — both depend only on the roll, neither on leveling — so this is a standalone milestone that needs no persistent hero, progression, or party.

```
        DADOS + ficha mínima   (Hito 1, archivado)   ← raíz
              │
              ├── HP / condiciones   (this change)    ← Hito 2
              └── héroe persistente  (later)
```

Constraints inherited from the codebase:
- **The system owns the number (D1 from Milestone 1).** The d20 is rolled in `dados.py` (pure, deterministic, seeded-RNG-injectable); the narrator declares a *band*, never a raw DC, and `BANDA_A_DC` maps it. Damage MUST follow the identical shape or the contract becomes incoherent.
- **The turn is two-phase for checks**: phase 1 declares `requiere_tirada`; the backend rolls; phase 2 narrates honoring the tier. There are two paths to keep in parity: synchronous `avanzar_turno` and the SSE `avanzar_turno_stream`.
- **Cosmos is schemaless and backward compatibility is a hard rule**: every new persisted field MUST deserialize safely on legacy partidas (precedents: `atributos`, `tirada`, `fase_narrativa`, `resumen_historia`).
- **The LLM contract is a strict JSON schema** injected into the system prompt; `_invocar_llm_con_reintento` does exactly one retry feeding back the validation error. Contract changes bump `PROMPT_VERSION` and are logged in `docs/prompts.md`.
- **World-state mutations are LLM-declared, service-applied**: the model emits `actualizaciones_estado`; `_aplicar_actualizaciones` applies them. Inventory already supports `quitar_inventario`.
- **The finished-game path already exists**: `EstadoPartida.FINALIZADA` + `TipoFinal.FRACASO` + `razon_fin`.

## Goals / Non-Goals

**Goals:**
- Hit points on the character whose maximum derives from Constitución, persisted, with safe legacy defaults.
- Damage owned by the system as a **fraction of `pv_max`**; the narrator picks a severity band, never a number.
- Damage and conditions that can be applied **with or without** a preceding check.
- Conditions that mechanically modify rolls (`desventaja`) and tick HP (`dano_por_turno`), with durations the system manages.
- Death by direct game-over at 0 HP, reusing the existing failure ending.
- A recovery valve (rest + inventory potions) so the failure→damage→disadvantage loop is not a one-way ratchet to death.
- Determinism under test for damage, condition ticking, and the new disadvantage roll.
- Full backward compatibility for partidas created before this change.

**Non-Goals:**
- Death saves or a downed-but-not-out state (explicit Milestone-1 non-goals; stays a hard game-over here).
- Condition effects beyond `desventaja` and `dano_por_turno` (no `vulnerable`, `no_puede_actuar`, etc. in v1).
- Persistent/leveling heroes, XP, or HP that grows with progression — `pv_max` is fixed per partida.
- Party / companions (explicitly dropped by the user for now).
- Advantage (2d20-keep-best) as a player-facing mechanic — only disadvantage is introduced, as the cost side.
- Typed damage / resistances, armor, or any combat-mode subsystem.

## Decisions

### D1: Damage as a fraction of `pv_max`, system-owned (mirrors Milestone-1 D1)

The narrator declares a **severity band** (`rasguno`, `leve`, `grave`, `severo`, `mortal`); the system owns a fixed `BANDA_SEVERIDAD_A_FRACCION` map and computes `damage = ceil(fraccion * pv_max)` (at least 1 for any non-zero band; `mortal` ⇒ drop to 0). **Why fraction over flat damage:** the model never needs to know the pool size to calibrate a meaningful hit, exactly as difficulty bands free it from guessing a DC. Flat numbers would force the model to reason about `pv_max` and would drift. *Alternative rejected:* narrator-supplied HP amount — the same untrustworthy theater D1 rejected for dice.

```
rasguno → ~5%    leve → ~15%    grave → ~30%    severo → ~50%    mortal → 100%
(exact fractions are a system-owned tuning table, monotonically increasing)
```

### D2: A `consecuencia` block in the turn schema, independent of `requiere_tirada`

The turn schema gains an optional `consecuencia`: `{ dano: severidad | null, condicion_aplicar: {...} | null, condicion_quitar: nombre | null, descanso: bool, curar_pocion: nombre | null }`. It is a **sibling** of `requiere_tirada`, not nested under it, so an ambient hazard can harm without a roll and a failed check can attach a cost. **Why a single sibling block:** keeps damage, conditions, and healing as one declarative consequence the service applies in one place (`_aplicar_actualizaciones`), and decouples "was there a roll?" from "was there a cost?". *Alternative rejected:* hanging damage off the roll result — would forbid trap/poison damage and conflate two concerns.

### D3: Conditions modify the Milestone-1 roll (`desventaja` = 2d20-keep-worst)

A `Condicion` carries `tipo`, `efecto` (`desventaja` | `dano_por_turno`), and `duracion`. When resolving a check, `dados.py` consults the character's active conditions: if any grants `desventaja` on the relevant roll, it rolls two d20s and keeps the **worse**, then applies the existing nat-20/nat-1 and total-vs-DC rules to the kept die. **Why reopen `dados.py`:** disadvantage is the mechanic that makes a condition *felt* on the dice the player already trusts; it is the cleanest tie-back to Milestone 1. The function stays pure and seeded-RNG-injectable — it just takes the active conditions (or a precomputed `desventaja: bool`) as an argument. *Alternative rejected:* purely narrative conditions — cheaper (no `dados.py` change) but conditions would carry no weight, defeating the milestone.

`dano_por_turno` is applied by the **service** at the start of each turn (not by `dados.py`), since it mutates `pv_actual` rather than a roll.

### D4: Death is a direct game-over reusing the existing failure path

When `pv_actual` reaches 0 (from damage or a `dano_por_turno` tick), the service sets `EstadoPartida.FINALIZADA`, `TipoFinal.FRACASO`, and a `razon_fin`, exactly like an LLM-declared narrative ending. **Why reuse over a new mechanic:** the finished-game path, UI, and persistence already exist; death saves were a Milestone-1 non-goal. *Alternatives rejected:* death-saving throws (ritual without justified value yet); downed-but-not-out (needs a party or a self-revive economy that doesn't exist).

### D5: Recovery via rest and inventory potions — the anti-death-spiral valve

Healing raises `pv_actual` toward `pv_max` (never above). It comes from a narrator-declared `descanso` (a fraction or full restore) and from consuming a potion named in `curar_pocion`, which the service removes via the existing `quitar_inventario` mechanism. **Why this matters mechanically, not just narratively:** without a valve, `fracaso → daño → desventaja → más fracaso → muerte` is a one-way ratchet. Rest + potions give the player and narrator a way out that uses systems already present (inventory). *Alternative rejected:* automatic regeneration per turn — removes tension and trivializes damage.

### D6: Persistence shape and backward compatibility

- `Personaje` gains `pv_max: int`, `pv_actual: int`, `condiciones: list[Condicion] = []`. For legacy docs (no fields), a model-level default/validator derives `pv_max` from the (default-10) Constitución, sets `pv_actual = pv_max`, and `condiciones = []` — mirroring the `Atributos.neutral()` precedent.
- `Condicion` is a new model (`tipo`, `efecto`, `duracion`); `duracion` is either an int turn-count or a sentinel for "until healed"/"until event".
- `PROMPT_VERSION` bumps; `docs/prompts.md` gets a changelog entry.

**Why:** mirrors the established schemaless-default pattern already used across the domain models, so no data backfill is needed.

### D7: `pv_max` derivation lives in the system, computed from Constitución

Creation derives `pv_max` from the generated Constitución score with a fixed formula (a base pool plus a Constitución-driven term), owned by the service — the creation LLM never emits HP. **Why:** keeps HP authoritative and consistent with D1; the sheet already generates Constitución, so HP is a pure function of existing data. The exact formula is a tuning knob (see Open Questions).

## Risks / Trade-offs

- **Death spiral** (failure → damage → disadvantage → more failure → death) → Mitigated by D5 (rest + potions) and by the narrator's discretion over when to attach a consequence; severity bands let small failures cost little.
- **Narrator over-punishes** (declares `severo`/`mortal` too freely) → Prompt guidance with explicit band-selection rules and examples; fractions keep small bands genuinely small; QA `feedback` loop can flag incoherence.
- **Reopening `dados.py` regresses Milestone-1 determinism** → Keep the function pure; pass `desventaja: bool` (or the active conditions) as an argument; add seeded tests for both the single-die and keep-worst paths before touching resolution.
- **Two-call/stream parity drift for the new consequence application** → Factor damage/condition/heal application and the death check into one shared helper used by both `avanzar_turno` and `avanzar_turno_stream` (the same approach Milestone 1 used for the roll).
- **Legacy partidas with default Constitución get a flat baseline pool** → Acceptable; they were created before HP existed and remain fully playable at the baseline.
- **Mid-stream death** (a `dano_por_turno` tick kills before the narration streams) → Resolve the tick and the death check before phase-2 streaming begins, so the game-over is decided up front, consistent with how the roll is resolved before streaming.

## Migration Plan

1. Add domain fields with safe defaults (`Personaje.pv_max`/`pv_actual` derived from Constitución; `condiciones=[]`; new `Condicion` model and enums). No data backfill — Cosmos deserializes legacy docs with the defaults.
2. Implement the damage/condition/heal helpers and the disadvantage roll as pure, unit-tested functions (severity→fraction map; condition tick + duration decrement; `dados.py` keep-worst). Seeded tests first.
3. Extend the turn schema with the `consecuencia` block; extend turn/resolution prompts to teach band selection, condition apply/clear, and rest/potion healing; derive `pv_max` at creation. Bump `PROMPT_VERSION`; add the `docs/prompts.md` changelog entry.
4. Wire consequence application + the death check into both turn paths via the shared helper; surface `pv_actual`/`pv_max`, conditions, and damage-taken in API responses and the frontend (health bar + condition badges).
5. Rollback: revert the prompt/schema version; persisted `pv_*`/`condiciones` fields are additive and inert if the resolution code is removed, so old and new clients coexist without corruption.

## Open Questions

- **`pv_max` formula:** what base pool and Constitución term give a curve where ~3–4 serious hits are lethal? (Tuning knob; a starting point is a flat base plus a multiple of the Constitución modifier.)
- **Severity → fraction values:** the exact percentages per band (and whether `mortal` is always an instant 0 or a very large fraction that a high pool could rarely survive).
- **`dano_por_turno` magnitude:** flat HP, or itself a small fraction of `pv_max`?
- **Rest restore amount:** full heal, or a fraction — and can the narrator rest mid-danger, or only in safe beats (prompt-guided)?
- **Disadvantage scope:** does a condition impose disadvantage on *all* checks, or only on checks of a related ability (e.g. `aturdido` only on physical rolls)? v1 leans "all checks while active" for simplicity; per-ability targeting is a later refinement.
