## 1. Domain & schema models

- [x] 1.1 Add `FaseNarrativa` StrEnum (`introduccion`, `desarrollo`, `climax`, `resolucion`) to `app/models/domain.py`
- [x] 1.2 Add `fase_narrativa` (default `introduccion`), `tension` (int, default 1), and `resumen_historia` (str, default "") to `WorldState`
- [x] 1.3 Add a required `arco` object (`fase_narrativa` enum, `tension` int 0–10) and required `resumen_historia` (string) to `TURNO_JSON_SCHEMA` in `app/models/llm_schema.py`
- [x] 1.4 Add matching Pydantic fields to `TurnoLLMResponse` (e.g. an `ArcoLLM` model + `resumen_historia`)

## 2. Prompts

- [x] 2.1 Rewrite `SYSTEM_PROMPT_TURNO`: replace turn-budget pacing with phase + tension rules; instruct to escalate tension, advance phase, and only finalize on `climax`/`resolucion` outcome or a terminal player choice; require foreshadowing before terminal outcomes
- [x] 2.2 Remove all "15-25 turnos" / turn-budget language from `SYSTEM_PROMPT_TURNO`, `SYSTEM_PROMPT_CREACION`, and `build_creacion_user_prompt` (objective no longer scoped to a turn count)
- [x] 2.3 Rewrite `build_turno_user_prompt`: drop the `tipos_accion` parameter and the per-turn archetype instruction; inject current `fase_narrativa`, `tension`, and `resumen_historia`; remove the "Turno actual: N (aventura típica: 15-25 turnos)" line; feed `resumen_historia` as memory instead of dumping the full `eventos_clave` list
- [x] 2.4 Bump `PROMPT_VERSION` to `2.0.0` and add a changelog entry in `docs/prompts.md`

## 3. Service layer

- [x] 3.1 Remove the `turno_actual >= max_turnos_por_partida` check and `LimiteTurnosExcedidoError` raise from `avanzar_turno`
- [x] 3.2 Remove the same check/raise from `_avanzar_turno_stream_impl`
- [x] 3.3 Remove `_seleccionar_tipos_accion`, the `_TIPOS_ACCION` table, and all `tipos_accion` call sites
- [x] 3.4 In `_aplicar_actualizaciones` (or equivalent), persist `fase_narrativa`, `tension`, and `resumen_historia` from the LLM response into `world_state`
- [x] 3.5 Initialize arc fields on creation in `crear_partida` (`introduccion`, tension 1, empty/opening summary) — satisfied by `WorldState` field defaults

## 4. Config & exceptions cleanup

- [x] 4.1 Remove `max_turnos_por_partida` from `app/core/config.py`
- [x] 4.2 Remove `LimiteTurnosExcedidoError` from `app/core/exceptions.py` and its HTTP mapping in `app/main.py` (no specific mapping existed; generic `AppError` handler unchanged)
- [x] 4.3 Remove `MAX_TURNOS_POR_PARTIDA` from `CLAUDE.md` env-var table and `backend/.env.example`

## 5. Tests (write failing first, then implement)

- [x] 5.1 Test: advancing a partida beyond the former limit succeeds and never raises a turn-limit error
- [x] 5.2 Test: a turn response persists `fase_narrativa`, `tension`, and `resumen_historia` into `world_state`
- [x] 5.3 Test: the next turn prompt includes current arc state and `resumen_historia` and no longer contains turn-budget text
- [x] 5.4 Test: narrator-driven ending (`finalizada` + `final` + `razon_fin`) flips `metadata.estado` and rejects further turns with `PartidaFinalizadaError`
- [x] 5.5 Test: a pre-change partida document (no arc fields) deserializes with defaults and advances a turn successfully
- [x] 5.6 Update/remove existing tests referencing `max_turnos_por_partida`, `LimiteTurnosExcedidoError`, or `_seleccionar_tipos_accion`

## 6. Verify

- [x] 6.1 `ruff check .` and `ruff format .` clean
- [x] 6.2 `pytest` green (92 passed)
- [x] 6.3 Manual smoke (requires live Azure Foundry + Cosmos): create a partida, advance past 25 turns, confirm it keeps playing; force a terminal choice and confirm a `fracaso` ending with `razon_fin`; confirm the end screen renders `final`/`razon_fin`
