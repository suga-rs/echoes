## Context

Today the narrator's pacing comes entirely from the turn counter. `MAX_TURNOS_POR_PARTIDA` (default 25) is enforced as a hard error in both the sync and stream paths, and the prompts repeat "aventura típica: 15-25 turnos" / "objetivo alcanzable en 15-25 turnos" to push the story toward a close. The ending machinery already exists end-to-end: the LLM returns `estado_aventura.tipo = "finalizada"` with a `final` (`exito`/`fracaso`/`ambiguo`) and `razon_fin`, the service flips `metadata.estado` to `FINALIZADA`, and subsequent turns raise `PartidaFinalizadaError`.

Two problems follow. First, the turn count does double duty (cost cap + pacing clock); removing it for narrative reasons orphans the pacing. Second, consistency relies on the last 4 turns verbatim plus an *unbounded* `eventos_clave`/`pistas`/`npcs` dump — fine at 25 turns, degrading at 60+. Action options are also forced into predetermined archetypes per turn by `_seleccionar_tipos_accion`, which can produce options that don't fit the fiction.

State persists in Cosmos DB (schemaless), so additive model fields deserialize safely on old documents. `PROMPT_VERSION` is logged and persisted per partida for auditing prompt/contract changes.

## Goals / Non-Goals

**Goals:**
- Replace the turn-count clock with a persisted narrative arc (`fase_narrativa` + `tension`) the LLM advances and reads back.
- Make turns truly unlimited — remove the cap and its error entirely.
- Keep long games consistent via a rolling `resumen_historia` instead of an unbounded event dump.
- Make narrator-driven endings (win / death / lost objective) fire on narrative outcome with foreshadowing, not on a turn budget.
- Let action options emerge from the situation, dropping the forced archetype injection.

**Non-Goals:**
- No RAG / vector retrieval over turn history (Layer 3 deferred).
- No UI for tension/phase — arc state is internal to the narrator.
- No reintroduction of any turn ceiling, hard or soft (cost is accepted as unbounded per the request).
- No change to image generation policy (first + last turn auto, rest on demand).

## Decisions

### 1. Arc state lives in `WorldState`, set by the LLM each turn
Add `fase_narrativa: FaseNarrativa` (enum: `introduccion`/`desarrollo`/`climax`/`resolucion`) and `tension: int` (0–10) to `WorldState` in `domain.py`, with defaults `introduccion`/`1` so pre-existing Cosmos documents deserialize cleanly. The turn JSON schema gains a required `arco` object (`fase_narrativa`, `tension`); the user prompt injects the current values. `_aplicar_actualizaciones` writes them back.

*Why here:* world_state is already the persisted, fed-back state container and the established pattern. *Alternative considered:* a separate `MetadataPartida` field — rejected; arc is narrative state, not audit metadata, and it belongs next to `objetivo`/`ubicacion_actual` that the narrator already reasons over.

### 2. Pacing is expressed as rules over phase + tension, not numbers
`SYSTEM_PROMPT_TURNO` is rewritten to instruct: advance the phase as the story develops, escalate `tension` toward `climax`, and only finalize when in/after `climax` (objective won/lost) or on a clearly terminal player choice. All "15-25 turnos" language is removed from both system and user prompts and from `SYSTEM_PROMPT_CREACION` (objective no longer scoped to a turn budget).

*Why:* dramatic structure is intrinsic and survives unlimited length; the number was an arbitrary proxy.

### 3. Rolling summary replaces the unbounded event dump in the prompt
Add `resumen_historia: str` to `WorldState`; the turn schema gains a required `resumen_historia` the LLM rewrites each turn. `build_turno_user_prompt` feeds `resumen_historia` as the narrator's memory and stops dumping the full `eventos_clave` list (the structured `eventos_clave`/`pistas`/`npcs` lists are still persisted for state checks, but the prompt leans on the summary plus last-N turns). Last-4 verbatim window stays.

*Why:* keeps prompt size roughly constant as turns grow. *Alternative considered:* truncating the raw lists to last-N — rejected; loses older-but-important facts that a narrator-curated summary keeps.

### 4. Remove the cap and its error, both paths
Delete the `turno_actual >= max_turnos_por_partida` checks in `avanzar_turno` and `_avanzar_turno_stream_impl`, remove `LimiteTurnosExcedidoError` from `exceptions.py` and its mapping in `main.py`, and remove `max_turnos_por_partida` from `config.py` and `CLAUDE.md`. `turno_actual` keeps incrementing for ordering/auditing only.

### 5. Drop forced action archetypes
Remove `_seleccionar_tipos_accion` and the `_TIPOS_ACCION` table; `build_turno_user_prompt` no longer takes `tipos_accion`. The system prompt's existing "MEANINGFULLY DIFFERENT" rule and good/bad examples carry option variety.

*Why:* the forced sequence fought "respect the player's decisions" by constraining the narrator to predetermined intentions regardless of scene.

### 6. Bump `PROMPT_VERSION` to 2.0.0
Schema + prompt contract changed (breaking for the LLM contract). The per-partida recorded version lets old and new games stay correlatable in telemetry.

## Risks / Trade-offs

- **Unbounded cost** (no turn cap) → Accepted explicitly by the request. Telemetry already records per-call usage; cost can be monitored, and a ceiling can be reintroduced later as a separate change if needed.
- **Narrator rambles or never ends** (no numeric pressure) → Mitigated by explicit phase/tension rules plus the existing objective; `tension` escalation and `climax` gating give the model a concrete "wrap up now" signal.
- **Summary drift / lossy memory** (model rewrites `resumen_historia` each turn and could drop facts) → Mitigated by keeping structured `world_state` (inventory, NPCs, eventos_clave, pistas) authoritative for state checks; the summary is narrative memory, not the source of truth for state.
- **Abrupt/unfair deaths** → Mitigated by the foreshadowing requirement in the prompt and the tension signal preceding terminal outcomes.
- **Schema/contract regressions** → The existing one-shot retry on validation failure (`_invocar_llm_con_reintento`) still applies; add tests asserting the new required fields and that no turn-limit error path remains.
- **Old partidas without arc fields** → Additive fields with defaults; verify `/resume` and turn advance on a pre-change document.

## Migration Plan

1. Additive model + schema changes; deploy backend. Old Cosmos documents deserialize with arc/summary defaults.
2. Bump `PROMPT_VERSION`; new turns use the new contract. In-flight partidas continue — first new turn populates arc/summary fields.
3. No data backfill required. No frontend deploy required (no UI change); confirm the end screen renders `final`/`razon_fin`.
4. Rollback: revert backend; arc/summary fields on documents are ignored by the old code (schemaless), and the old turn-limit check returns.

## Open Questions

- Initial `tension` value on creation (1 vs 0) — minor; default to 1 to signal a live story. Not blocking.
- Whether `creacion` should also emit an initial `resumen_historia` or let it start empty and fill on turn 2 — default: start from the opening narrative, populated on the first advance. Not blocking.
