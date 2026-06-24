## Why

The d20 skill checks shipped in Milestone 1 (`add-d20-skill-checks`) deliberately left failure **purely narrative**: a `fracaso` or even a `fracaso_critico` produces nothing the player carries forward — it is just uglier prose. Without a cost that persists, risk still isn't *felt*, so the dice only half-deliver on "play it at a table." This is Milestone 2 of the layered D&D-feel vision and it is the natural sibling of the dice (both depend only on the roll, neither on leveling): it gives the existing d20 **teeth** by turning failure into a mechanical consequence — hit points the player can lose and conditions that bias the next roll.

## What Changes

- **Hit points on the character.** `Personaje` gains `pv_max` and `pv_actual`. `pv_max` is derived from Constitución at creation (the existing six-attribute sheet). Legacy partidas deserialize at a Constitución-10 baseline, full health, no conditions.
- **Damage as a fraction of max HP, system-owned.** Mirroring Milestone 1's D1 ("the system owns the number, the narrator only adjudicates"), the narrator declares a **severity band** (`rasguno`, `leve`, `grave`, `severo`, `mortal`) — never a raw HP number. The system maps each band to a **fraction of `pv_max`**, so damage stays meaningful regardless of pool size and the model cannot silently move the goalposts. Damage banding is the consequence analog of the difficulty banding.
- **Damage independent of a check.** The narrator can apply a consequence (damage and/or a condition) with **no preceding roll** — a sprung trap or ambient poison hurts without a check. Consequence is its own declared block, decoupled from `requiere_tirada`.
- **Conditions that mechanically modify rolls.** A condition has a type (e.g. `envenenado`, `sangrando`, `aturdido`), an effect, and a duration. v1 ships two effects: **`desventaja`** (the d20 resolution rolls 2d20 and keeps the worst) and **`dano_por_turno`** (a small per-turn HP tick). This means the Milestone-1 dice resolution now consults active conditions before classifying a roll.
- **Death by direct game-over.** When `pv_actual` reaches 0 the partida ends, reusing the existing `EstadoPartida.FINALIZADA` + `TipoFinal.FRACASO` path. No death saves, no "downed but not out" (both were explicit Milestone-1 non-goals).
- **Recovery as the anti-death-spiral valve.** HP returns through narrator-declared **rest** and through **potions** consumed from the existing inventory (the `quitar_inventario` mechanism already removes the item). Without this, the failure→damage→disadvantage→more-failure loop would be a one-way ratchet to death.
- **HP and conditions surfaced in the UI.** A health bar (`pv_actual` / `pv_max`), condition badges, and the damage applied this turn — the cost is part of the product, not hidden bookkeeping.
- The contract bumps `PROMPT_VERSION` and adds a `docs/prompts.md` changelog entry.

This change is scoped to Milestone 2. Death saves, downed-but-not-out, persistent/leveling heroes, party/companions, and condition effects beyond `desventaja` + `dano_por_turno` are explicitly **out of scope**.

## Capabilities

### New Capabilities
- `hp-conditions`: Hit points on the character (max derived from Constitución), system-owned damage declared by the narrator as a severity band mapped to a fraction of max HP, conditions with mechanical effects (`desventaja`, `dano_por_turno`) and durations, death by direct game-over at 0 HP, and recovery via rest and inventory potions. Includes persistence shape and backward-compatible defaults for legacy partidas.

### Modified Capabilities
- `skill-checks`: The d20 resolution now consults the character's active conditions; a condition granting `desventaja` makes the relevant roll resolve as 2d20-keep-worst before tier classification. The roll remains server-authoritative and deterministic under test.
- `narrative-creation`: Character creation derives the character's `pv_max` from the generated Constitución score and starts the character at full health with no conditions.

## Impact

- **Backend domain** (`app/models/domain.py`): `Personaje` gains `pv_max`, `pv_actual`, and `condiciones: list[Condicion]`; new `Condicion` model and enums (severity band, condition type, condition effect). Legacy partidas deserialize with safe defaults (full HP at CON-10 baseline, no conditions).
- **LLM contract** (`app/models/llm_schema.py`): `TURNO_JSON_SCHEMA` gains an optional `consecuencia` block (severity band + condition to apply/remove + rest/heal intent) that is independent of `requiere_tirada`. `PROMPT_VERSION` bumps.
- **Dice resolution** (`app/services/dados.py`): roll resolution accepts active conditions and applies `desventaja` (2d20-keep-worst) while staying pure and deterministic for seeded tests.
- **Prompts** (`app/services/prompts.py`): the turn/resolution prompts teach the narrator when to apply damage (with/without a check), how to pick a severity band, how to apply/clear conditions, and how to grant rest/potion healing.
- **Service** (`app/services/partida_service.py`): `_aplicar_actualizaciones` applies fractional damage, adds/removes conditions, ticks `dano_por_turno` and condition durations, applies rest/potion healing, and triggers game-over at `pv_actual <= 0`. Parity across `avanzar_turno` and `avanzar_turno_stream`.
- **API** (`app/api/partidas.py`) and **frontend** (`partida-store.ts`, character/turn UI): surface `pv_actual`/`pv_max`, the condition list, and the damage applied this turn (health bar + condition badges).
- **Docs** (`docs/prompts.md`): changelog entry for the contract bump.
- No new external dependencies; damage and condition resolution use the standard library and reuse the seeded RNG already in `dados.py`.
