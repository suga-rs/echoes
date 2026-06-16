## Why

The narrator's only sense of dramatic time is the turn counter: every prompt injects "aventura típica: 15-25 turnos", and `MAX_TURNOS_POR_PARTIDA` both caps cost and forces a wrap-up. This produces flat pacing, endings that feel arbitrary (driven by a budget running out rather than by the story), and consistency that degrades as the unbounded event list grows. We want stories that escalate, end when the player wins, dies, or closes off their objective, and stay coherent over an unlimited number of turns.

## What Changes

- **BREAKING**: Remove the turn-count pacing model. Turns become **truly unlimited** — `MAX_TURNOS_POR_PARTIDA` and `LimiteTurnosExcedidoError` are removed; no hard or soft turn ceiling remains.
- Replace the turn counter as the narrator's clock with a persisted **narrative arc**: `fase_narrativa` (introducción → desarrollo → clímax → resolución) and a `tension` value (0–10) that the LLM advances and reads back each turn. These are **internal only** — no UI is added.
- Add a rolling **`resumen_historia`** (story-so-far summary) the narrator maintains each turn, fed into the prompt in place of the unbounded `eventos_clave` dump, so long games stay consistent.
- Strengthen narrator-driven endings: `estado_aventura.tipo = "finalizada"` gates on the story reaching `resolución` / a terminal player choice (death, lost objective, win) **with foreshadowing**, not on a turn number. The end-to-end machinery already exists; this change re-aims it.
- **Soften the forced action archetypes**: drop the per-turn `_seleccionar_tipos_accion` injection; options emerge from the situation, governed by the existing "meaningfully different" rule.
- Bump `PROMPT_VERSION` (prompt + JSON contract change). Existing partidas keep their recorded version for auditability.
- Out of scope (explicitly deferred): RAG / vector retrieval over turn history (Layer 3); any tension/phase UI.

## Capabilities

### New Capabilities
- `narrative-arc`: How the narrator paces a story (arc phase + tension), maintains long-game consistency (rolling summary + structured world state), generates situation-driven options, and ends a partida on a won/lost/terminal outcome — independent of any turn count.

### Modified Capabilities
<!-- No existing captured spec covers the gameplay loop; the relevant behavior is introduced as the new narrative-arc capability above. -->

## Impact

- **Backend**
  - `app/models/llm_schema.py` — add `fase_narrativa`, `tension`, `resumen_historia` to the turn schema + Pydantic; relax `estado_aventura` guidance.
  - `app/models/domain.py` — add arc fields to `WorldState`; persist them (Cosmos is schemaless, old games default safely).
  - `app/services/prompts.py` — rewrite `SYSTEM_PROMPT_TURNO` / user prompt (arc-driven pacing, foreshadowed endings, situation-driven options); drop turn-budget language; bump `PROMPT_VERSION`.
  - `app/services/partida_service.py` — remove `LimiteTurnosExcedidoError` raises and the cap check (both sync and stream paths); apply new arc/summary state; remove `_seleccionar_tipos_accion`.
  - `app/core/config.py` — remove `max_turnos_por_partida` setting.
  - `app/core/exceptions.py` — remove `LimiteTurnosExcedidoError` (and its HTTP mapping in `main.py`).
  - Tests under `backend/tests/` referencing the turn limit / archetypes.
- **Frontend**: none required (no UI for arc state). Confirm the end-of-game screen already renders `final` / `razon_fin` from `TurnoResponse`.
- **Docs**: `CLAUDE.md` env-var table and `docs/prompts.md` changelog.
