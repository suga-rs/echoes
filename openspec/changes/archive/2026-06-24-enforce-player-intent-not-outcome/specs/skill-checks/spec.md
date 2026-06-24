## ADDED Requirements

### Requirement: Player declares intent, never resolution

The narrator SHALL treat the player's action text as the player's *intent* (what the character attempts), never as the *outcome* of that attempt. When the player's action text asserts a resolution — that the action succeeds, that it kills or defeats an adversary, that an NPC is convinced, or any other result the player is not entitled to author — the narrator SHALL disregard the asserted resolution and resolve only the underlying attempt.

The narrator SHALL NOT downgrade an uncertain action to "no check" because the player phrased it as already-succeeded. An attempt whose outcome is not guaranteed SHALL declare a check (per "Narrator declares checks, never raw difficulty") regardless of how the player worded it. An attempt that is impossible given the situation SHALL be narrated as a failed attempt without a roll; the player's asserted success does not make it real.

This requirement constrains only the per-turn player action (`SYSTEM_PROMPT_TURNO` / `build_turno_user_prompt`); creation and the narrator-generated options are out of scope.

#### Scenario: Player-asserted kill still triggers a check

- **WHEN** the player submits an action that asserts its own resolution for an uncertain attempt, such as "Realizo un último ataque al corazón del guardia y lo mato"
- **THEN** the narrator disregards the asserted kill and declares a check for the attack attempt (one ability, one difficulty band)
- **AND** the d20 result, not the player's wording, determines whether the guard dies

#### Scenario: Player-asserted success on a contested action is not honored

- **WHEN** the player submits "Convenzo al guardia y me deja pasar" where persuading the guard is uncertain
- **THEN** the narrator declares a `carisma` check rather than narrating the guard standing aside
- **AND** the outcome is resolved by the roll

#### Scenario: Player-asserted outcome on an impossible action is narrated as a failed attempt

- **WHEN** the player submits an impossible action phrased as success, such as "Agito la mano y el guardia explota"
- **THEN** the narrator narrates the failed attempt in a single narration without declaring a check
- **AND** the asserted outcome does not occur

#### Scenario: Genuine player decisions are still honored

- **WHEN** the player's action expresses only an intention or a choice (for example "Ataco al guardia", "Intento esconderme", "Le ofrezco monedas") without asserting the result
- **THEN** the narrator honors the decision and resolves it through the normal check-or-narrate flow
