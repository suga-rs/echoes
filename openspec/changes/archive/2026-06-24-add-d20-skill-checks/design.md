## Context

Echoes resolves every turn with a single LLM call: the model authors the outcome of the player's action directly. There is no uncontrolled risk, so outcomes never feel earned. This change introduces real, server-rolled d20 skill checks plus a minimal six-attribute character sheet to modify them — Milestone 1 of a layered "feel like a D&D session" vision.

This milestone is the **irreducible root** of that vision. Dependencies established during exploration:

```
            DADOS + ficha mínima (this change)   ← root
                  ├── HP / condiciones            (later)
                  └── héroe persistente           (later)
                            └── progresión/nivel  (later)
                                  └── companions  (later)
```

Constraints inherited from the codebase:
- The LLM contract is a strict JSON schema injected into the system prompt; `PartidaService._invocar_llm_con_reintento` does exactly one retry feeding back the validation error before raising `RespuestaLLMInvalidaError`.
- Cosmos is schemaless and the repo treats backward compatibility as a hard rule: every new persisted field must deserialize safely on legacy partidas (see the `fase_narrativa`, `resumen_historia`, `usa_referencia_visual` precedents).
- Contract changes bump `PROMPT_VERSION` (currently `2.2.0`) and are logged in `docs/prompts.md`.
- There are two turn paths to keep in parity: synchronous `avanzar_turno` and the SSE `avanzar_turno_stream` (which streams the `narrativa` token-by-token via `_NarrativaExtractor`).

## Goals / Non-Goals

**Goals:**
- A real d20 rolled server-side whose result the narrator must honor, surfaced transparently to the player.
- Difficulty owned by the system via fixed bands; the model picks a band, never a number.
- A minimal, persisted six-attribute sheet that biases checks via standard modifiers.
- Determinism under test for both the dice roller and (existing) seed sampling.
- Full backward compatibility for partidas created before this change.

**Non-Goals:**
- HP / conditions, death saves, or any gradient-of-failure model (failure stays narrative this milestone).
- Persistent leveling heroes across adventures, XP, or progression.
- AI companions / party play, combat mode with initiative, rests, or loot with mechanical weight.
- A 2d6 / partial-success ladder — this milestone is deliberately d20-flavored to stay closest to D&D.
- Player-editable stats or manual point-buy; scores are narrator-generated at creation.

## Decisions

### D1: Real server-side d20, not LLM-narrated dice

The roll happens in Python (`random.Random`, injectable for tests), not inside the model. **Why:** the roll *moment* is the product; an LLM "rolling" is theater the player cannot trust and is not actually random. The model becomes an adjudicator of a fact, not the author of the outcome. *Alternative rejected:* asking the LLM to emit a roll value — invisible, unauditable, and biased.

### D2: Two-phase turn for checked actions

Phase 1 (LLM): given the action, decide whether a check is needed; if so emit `requiere_tirada = {habilidad, banda}` plus the in-fiction stakes. Backend rolls. Phase 2 (LLM): narrate the outcome honoring the result tier, and emit the usual options + state/arc updates.

```
player action ─▶ [phase 1 LLM]
                   │
            requiere_tirada?
             no │        │ yes
                ▼        ▼
        narrate fully   declare {habilidad, banda}
        (1 call, as     + stakes
         today)              │
                       backend: d20 + mod vs DC(banda)
                             │  → tier
                       [phase 2 LLM] narrate honoring tier
                             │
                       options + state/arc updates
```

**Why two calls over one:** preserves the dramatic beat (declare → roll → resolve) and lets the player see the d20 before the outcome is written. *Alternative rejected:* a single call that pre-writes both success and failure narrations — cheaper by one round-trip but loses the reveal beat and forces the model to write throwaway prose; it also scales badly if partial tiers are added later.

**Cost/latency note:** checked turns cost a second LLM round-trip. Trivial/impossible actions stay single-call, so not every turn pays it. The phase-1 call can be kept short (it needs the declaration and a setup sentence, not full prose).

### D3: Fixed difficulty bands, model picks the band

`trivial`=5, `facil`=10, `media`=15, `dificil`=20, `heroica`=25. The model emits a band enum; the system maps to the DC. **Why:** a model free to pick raw DCs is inconsistent and can move goalposts; bands keep difficulty legible and testable. *Alternative rejected:* model-supplied numeric DC.

### D4: Result tiers with nat-20 / nat-1 overrides

Tiers: `exito_critico`, `exito`, `fracaso`, `fracaso_critico`. Natural 20 ⇒ `exito_critico` and natural 1 ⇒ `fracaso_critico`, independent of modifier/DC; otherwise total ≥ DC ⇒ `exito`, else `fracaso`. **Why:** this is the recognizable D&D shape (crit/fumble) and gives the narrator richer outcome material than pass/fail without adopting a foreign partial-success system.

### D5: Six classic attributes (3–18) with standard modifier

`fuerza, destreza, constitucion, inteligencia, sabiduria, carisma`; modifier = `floor((score − 10) / 2)`. Generated at creation, biased to the player's description. **Why:** chosen over Fate-style approaches to stay closest to D&D as the user directed; the familiar stat names and the `(score−10)/2` curve are what reads as "a D&D sheet." The narrator maps free-text intent to one ability when declaring a check (it already interprets free text today).

### D6: Persistence shape and backward compatibility

- `Personaje` gains `atributos: Atributos` (six ints), defaulting all to 10 so legacy characters deserialize as +0 across the board.
- `TurnoHistorial` gains an optional `tirada` record (habilidad, banda, dc, d20, modificador, total, resultado) — `None` for unchecked turns and for all legacy turns.
- `MetadataPartida.prompt_version` continues to record the contract version; `PROMPT_VERSION` bumps to a new minor/major.

**Why:** mirrors the established schemaless-default pattern already used across the domain models.

### D7: Stream-path parity

`avanzar_turno_stream` keeps streaming the phase-2 `narrativa`. The phase-1 declaration is resolved before streaming begins; the SSE flow emits the roll (e.g. a `tirada` event) ahead of the `token` stream so the UI can animate the d20, then streams the outcome narration. **Why:** keeps the existing token-stream UX while inserting the roll reveal at the dramatically correct point.

### D8: 3D dice roll as a scripted-rotation overlay (vanilla three.js)

The roll is presented as a 3D d20 animation rendered with **vanilla `three.js`** in a `useEffect` (no physics engine, no react-three-fiber). The die tumbles and then eases ("settle") into the precomputed orientation for the server-rolled face, so the animation is pure theater over the authoritative number (consistent with D1).

**Why vanilla three over `@react-three/fiber`:** r3f v8 was tried first but its custom React reconciler accesses React internals (`ReactSharedInternals` / `ReactCurrentOwner`) that fail to resolve under the Next.js App Router bundler, throwing at runtime. For a single die, r3f's declarative reconciler adds no value and introduces that fragile coupling; driving three.js directly from a `useEffect` (manual `requestAnimationFrame` loop, dispose on unmount) is lighter and avoids the entire class of React-version coupling.

```
  tabla de 20 quaternions: "cara N → mirando a cámara"
    (computada una vez desde las normales del icosaedro; determinista)

  animación = TUMBLE (~1.2s giro multiaxis) + SETTLE (~0.6s lerp a la cara N)
            → staged reveal: d20 → +mod → total → vs DC → veredicto
            → auto-dismiss, paso a la narrativa
```

**Why scripted rotation over physics:** a WebGL physics engine (ammo.js/rapier) is multiple MB and tonally heavy for a brief beat in a text-first game; scripted rotation gives a real 3D die with full control of the landing face and *no rigged-physics problem*. *Alternatives rejected:* full physics lib (`@3d-dice/dice-box`) — max wow but heavy and tonally off; 2D pre-rendered (Lottie/sprite) — lightest but the number "pops" inauthentically.

- **Placement:** full-screen overlay reusing the existing Radix Dialog (`imagen-modal.tsx`) for backdrop, focus-trap, and a11y; auto-dismisses into the narration.
- **Latency masking:** the overlay plays during the phase-2 LLM call, converting the two-round-trip cost (see Risks) into suspense. Triggered by the `tirada` SSE event that precedes the token stream (D7).
- **Mesh:** procedural numbered icosahedron (number texture atlas) to avoid an external asset dependency; a pre-made GLTF d20 is a fallback if procedural numbering looks poor.
- **Crits:** `emissive` material glow — gold on nat-20, red on nat-1 — tying the tiers from `skill-checks` to a table-moment.
- **Loading & a11y:** lazy-loaded via `next/dynamic(..., { ssr: false })` so Three.js only loads on the first check; a `prefers-reduced-motion` (or load-failure) path renders the static staged-reveal card. The animation is enhancement only — the result is always available as text and asserted as data in tests, never as pixels.
- **Genre theming** (ornate gold / neon / bone per género, reusing the `ESTILO_POR_GENERO` idea) is a deliberate post-v1 delighter, out of scope here.

## Risks / Trade-offs

- **Extra latency on checked turns (two round-trips)** → Keep phase 1 minimal; only checked turns pay it; consider surfacing the d20 animation during the phase-2 wait so latency reads as suspense.
- **Model over-declares checks (asks for a roll on everything)** → Prompt guidance with explicit "trivial/impossible ⇒ no check" rules and few-shot examples; the single-call path remains the default for non-risky actions.
- **Model picks an ill-fitting ability for the action** → Acceptable looseness (a human DM also judges this); constrain to the six-enum and give mapping examples in the prompt.
- **Narrator contradicts the rolled tier in phase 2** → Phase-2 prompt states the tier as a hard constraint and the schema/QA feedback loop (existing `feedback` field) can flag incoherence.
- **Two-call flow drifts out of parity between sync and stream paths** → Factor the roll + tier classification into a shared helper used by both `avanzar_turno` and `avanzar_turno_stream`.
- **Legacy partidas mixing +0 stats with new checks feel flat** → Acceptable; neutral stats still roll and resolve, and these are pre-existing games.

## Migration Plan

1. Add domain fields with safe defaults (`Atributos` default 10; `TurnoHistorial.tirada` default `None`). No data backfill needed — Cosmos deserializes legacy docs with the defaults.
2. Extend creation schema/prompt to emit attributes; extend turn schema/prompts for phase 1 + phase 2; add the phase-2 resolution prompt. Bump `PROMPT_VERSION` and add a `docs/prompts.md` changelog entry.
3. Implement the dice roller + band map + tier classifier as a pure, unit-tested helper; wire it into both turn paths.
4. Surface the roll and the stat block in the API responses and frontend.
5. Rollback: revert the prompt/schema version; persisted `atributos`/`tirada` fields are additive and inert if the resolution code is removed, so old and new clients coexist without corruption.

## Open Questions

- Should `exito_critico` / `fracaso_critico` carry a mechanical nudge later (advantage, extra inventory/condition), or stay purely narrative this milestone? (Leaning purely narrative now.)
- Does the player ever get to *choose* which ability to attempt an action with (declaring approach), or is ability selection always the narrator's call? (This milestone: narrator's call.)
- Dice presentation is decided (D8): a scripted-rotation r3f 3D overlay with a static reduced-motion fallback, folded into this change.
- Mesh approach within D8: procedural numbered icosahedron vs imported GLTF d20 — to be settled during implementation based on how the procedural numbering reads.
