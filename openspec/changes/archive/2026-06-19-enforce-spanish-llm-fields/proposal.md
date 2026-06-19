## Why

Short, label-like LLM output fields — `objetivo`, `inventario`, and the action `opciones` — intermittently come back in English, breaking the product's Spanish-rioplatense constraint. The language is asserted globally and prose-centrically, but never pinned per-field for these short values; meanwhile the explicitly-English `_en` fields sit beside them in the same JSON object and prime English. `objetivo` is generated once at creation and persisted unchanged, so a single English slip poisons a game's display for its entire lifetime.

## What Changes

- Add a single explicit, bidirectional language rule to both system prompts (`SYSTEM_PROMPT_CREACION`, `SYSTEM_PROMPT_TURNO`): every text field is Spanish rioplatense **except** fields whose name ends in `_en`, which are English. This anchors the rule to the `_en` naming convention the model already honors.
- Add `description` annotations to the Spanish-facing leaky properties in both JSON schemas (`objetivo`, `inventario_inicial`, `agregar_inventario`/`quitar_inventario` items, `opciones`) stating they must be in Spanish rioplatense, reinforcing the rule where the model looks when emitting short fields.
- Bump `PROMPT_VERSION` since the prompt/contract changed.
- Add a one-off migration plan for already-created partidas whose persisted `objetivo` (and optionally inventory) is in English, so existing games are corrected rather than left poisoned.

## Capabilities

### New Capabilities
- `spanish-output-contract`: Defines the language contract for LLM output fields — all player-facing text is Spanish rioplatense except `_en`-suffixed fields — enforced in the prompts and schemas, plus a one-off remediation for legacy partidas persisted with English `objetivo`/inventory.

### Modified Capabilities
<!-- No existing capability's requirements change at the spec level; the language contract is a new cross-cutting concern not previously stated. -->

## Impact

- `backend/app/services/prompts.py` — `SYSTEM_PROMPT_TURNO`, `SYSTEM_PROMPT_CREACION`, `PROMPT_VERSION`.
- `backend/app/models/llm_schema.py` — `description` on `objetivo`, `inventario_inicial`, `agregar_inventario`, `quitar_inventario`, `opciones` (both schemas).
- `docs/prompts.md` — changelog entry for the new prompt version.
- One-off migration script/task over the Cosmos `partidas` container for legacy games.
- No API, frontend, or persisted-schema shape changes; values flow through untouched today.
