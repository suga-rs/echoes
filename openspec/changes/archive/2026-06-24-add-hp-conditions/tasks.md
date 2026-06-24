## 1. Domain model & backward-compatible persistence

- [x] 1.1 Add enums to `app/models/domain.py`: `BandaSeveridad` (`rasguno`, `leve`, `grave`, `severo`, `mortal`), `TipoCondicion` (`envenenado`, `sangrando`, `aturdido`, …), `EfectoCondicion` (`desventaja`, `dano_por_turno`).
- [x] 1.2 Add the `Condicion` model (`tipo`, `efecto`, `duracion`) with `duracion` as an int turn-count or a sentinel for "until healed"/"until event".
- [x] 1.3 Add `pv_max`, `pv_actual`, and `condiciones: list[Condicion]` to `Personaje`, with a default/validator that derives `pv_max` from Constitución and sets `pv_actual = pv_max`, `condiciones = []` for legacy docs (mirror `Atributos.neutral()`).
- [x] 1.4 Write tests: a legacy partida dict (no HP/condition fields) deserializes to full health at the CON-10 baseline with no conditions and stays playable.

## 2. Pure mechanics (HP, damage, conditions, disadvantage)

- [x] 2.1 Write failing tests for the severity→fraction map and `calcular_dano(pv_max, banda)` (at least 1 HP for any non-zero band; monotonic increase; `mortal` ⇒ 0; never below 0).
- [x] 2.2 Implement the severity→fraction table and `calcular_dano` (system-owned, pure).
- [x] 2.3 Write failing tests for `pv_max` derivation from Constitución (higher CON ⇒ larger pool); implement the derivation helper.
- [x] 2.4 Write failing tests for condition ticking: `dano_por_turno` subtracts each turn, turn-count durations decrement and expire, "until healed"/"until event" persist; implement the tick/duration helper.
- [x] 2.5 Write failing tests in `app/services/dados.py` for disadvantage: with `desventaja` active, resolution rolls two d20s and keeps the worse, applying nat-20/nat-1 and total-vs-DC to the kept die; deterministic under a seeded RNG. No-disadvantage path still rolls a single d20.
- [x] 2.6 Extend the `dados.py` resolution to accept `desventaja: bool` (or active conditions) and roll keep-worst, keeping the function pure and seeded-RNG-injectable.

## 3. LLM contract & prompts

- [x] 3.1 Add the optional `consecuencia` block to `TURNO_JSON_SCHEMA` (sibling of `requiere_tirada`): `dano` (severity band | null), `condicion_aplicar` (tipo/efecto/duracion | null), `condicion_quitar` (name | null), `descanso` (bool), `curar_pocion` (name | null). Add the Pydantic wrapper to `TurnoLLMResponse`.
- [x] 3.2 Update turn and resolution prompts in `app/services/prompts.py`: when to apply damage (with/without a check), how to pick a severity band, how to apply/clear a condition, how to grant rest/potion healing.
- [x] 3.3 Ensure creation derives `pv_max` from the generated Constitución at the service layer (the creation LLM does not emit HP); confirm `CREACION_JSON_SCHEMA` needs no HP field.
- [x] 3.4 Bump `PROMPT_VERSION` and add a `docs/prompts.md` changelog entry for the contract bump.
- [x] 3.5 Write tests: a turn response with a `consecuencia` block validates; an invalid severity band fails schema validation and the existing one-retry path feeds the error back.

## 4. Service wiring (apply consequences, death, parity)

- [x] 4.1 Write failing tests for a shared `aplicar_consecuencia` helper: fractional damage, add/remove condition, rest/potion healing capped at `pv_max`, potion removed via `quitar_inventario`, and game-over (`FINALIZADA` + `FRACASO` + `razon_fin`) when `pv_actual` reaches 0.
- [x] 4.2 Implement the shared helper and call it from `_aplicar_actualizaciones` (or alongside it) in `app/services/partida_service.py`.
- [x] 4.3 Apply the `dano_por_turno` tick + death check at the start of the turn, before phase-2 streaming begins, so a mid-stream death is decided up front.
- [x] 4.4 Pass the character's active `desventaja` state into the `dados.py` resolution when resolving a declared check.
- [x] 4.5 Wire the helper into both `avanzar_turno` and `avanzar_turno_stream`; add a parity test that both paths apply damage/conditions/death identically.

## 5. API & frontend surfacing

- [x] 5.1 Surface `pv_actual`, `pv_max`, active conditions, and damage-taken-this-turn in the relevant API responses/DTOs (`TurnoResponse`/`StateResponse` and resume).
- [x] 5.2 Extend the frontend store/types (`partida-store.ts`, `types.ts`) with HP and conditions; re-hydrate them on `/resume`.
- [x] 5.3 Add the health bar (`pv_actual`/`pv_max`) and condition badges to the character/turn UI; show that a cost was paid when a turn applies damage.

## 6. Verification

- [x] 6.1 Run `pytest`, `ruff check .`, and `ruff format .` in `backend/`; all green.
- [x] 6.2 Run `pnpm lint` and `pnpm typecheck` in `frontend/`; all green.
- [x] 6.3 Manually verify end-to-end: take damage with and without a check, acquire a `dano_por_turno` condition and watch a check resolve with disadvantage, heal via rest and via a potion (potion leaves inventory), and reach 0 HP to confirm the failure game-over.
