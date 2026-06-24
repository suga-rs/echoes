# hp-conditions

## Purpose

Turns the narrative-only failure of the d20 skill checks into a mechanical consequence. The character has hit points (max derived from Constitución); the narrator declares damage as a system-owned severity band mapped to a fraction of max HP (never raw HP), applies conditions with mechanical effects (`desventaja`, `dano_por_turno`) and durations, and the game ends in failure at 0 HP. Recovery comes from rest and inventory potions, the valve that keeps the failure→damage→disadvantage loop from being a one-way path to death. Legacy partidas deserialize at full health with no conditions.

## Requirements

### Requirement: Character has hit points derived from Constitución

The character SHALL have a maximum hit-point pool (`pv_max`) and a current hit-point value (`pv_actual`). `pv_max` SHALL be derived deterministically from the character's Constitución score at creation, such that a higher Constitución yields a larger pool. At creation `pv_actual` SHALL equal `pv_max`. Both values SHALL be persisted on the character. Partidas created before this change (no hit-point fields persisted) SHALL deserialize at a Constitución-10 baseline pool, at full health, with no conditions, and remain playable.

#### Scenario: New character starts at full health

- **WHEN** a new game is created
- **THEN** the character's `pv_max` is derived from its generated Constitución score
- **AND** `pv_actual` equals `pv_max`

#### Scenario: Higher Constitución yields a larger pool

- **WHEN** two characters are created, one with a higher Constitución than the other
- **THEN** the character with the higher Constitución has the larger `pv_max`

#### Scenario: Legacy partida deserializes at full health

- **WHEN** a partida persisted before this change is loaded
- **THEN** its character resolves to a Constitución-10 baseline `pv_max`, `pv_actual` equal to `pv_max`, and no conditions
- **AND** the partida remains playable

### Requirement: System owns damage; narrator declares a severity band

The narrator SHALL declare damage as a severity band (`rasguno`, `leve`, `grave`, `severo`, `mortal`) and SHALL NOT supply a numeric hit-point amount. The system SHALL own a fixed, monotonically increasing mapping from severity band to a fraction of the character's `pv_max`, and SHALL compute the damage as that fraction of `pv_max`, rounded so that any non-zero band removes at least 1 hit point. `mortal` SHALL reduce `pv_actual` to 0. Applying damage SHALL subtract the computed amount from `pv_actual`, never below 0.

#### Scenario: Severity band maps to a fraction of max HP

- **WHEN** the narrator declares `grave` damage against a character with `pv_max` 40
- **THEN** the system applies the `grave` fraction of 40 as hit-point loss
- **AND** the narrator's output contains no numeric hit-point amount

#### Scenario: Larger band removes more HP

- **WHEN** the same character takes `leve` damage versus `severo` damage
- **THEN** the `severo` band removes strictly more hit points than the `leve` band

#### Scenario: Mortal damage drops the character to zero

- **WHEN** the narrator declares `mortal` damage
- **THEN** `pv_actual` is reduced to 0

#### Scenario: Damage never drives HP below zero

- **WHEN** declared damage exceeds the character's current `pv_actual`
- **THEN** `pv_actual` is set to 0 and not a negative value

### Requirement: Damage and conditions are independent of a check

The narrator SHALL be able to apply a consequence (damage and/or a condition) on a turn that declared no check. The consequence block SHALL be independent of `requiere_tirada`, so an ambient hazard (a sprung trap, environmental poison) can harm the character without a preceding roll. The narrator SHALL also be able to apply a consequence on the failing outcome of a check.

#### Scenario: Ambient hazard damages without a roll

- **WHEN** the player triggers a trap and the narrator declares no check
- **THEN** the narrator may still declare damage and/or a condition for that turn
- **AND** the damage is applied without any d20 roll

#### Scenario: Failed check carries a consequence

- **WHEN** a declared check resolves to `fracaso` or `fracaso_critico`
- **THEN** the narrator may declare damage and/or a condition as the cost of the failure

### Requirement: Conditions with mechanical effects and durations

The character SHALL carry a list of active conditions. Each condition SHALL have a type (e.g. `envenenado`, `sangrando`, `aturdido`), a mechanical effect, and a duration. The supported effects in this version SHALL be exactly `desventaja` (the relevant roll resolves as the worse of two d20s — see the `skill-checks` capability) and `dano_por_turno` (a fixed small hit-point loss applied at the start of each turn while the condition is active). Duration SHALL be expressed as a turn count, "until healed", or "until a narrative event". The narrator SHALL be able to add a condition and to clear an existing condition. The system SHALL decrement turn-count durations each turn and remove conditions whose duration has elapsed.

#### Scenario: Condition is added to the character

- **WHEN** the narrator declares that the character becomes `envenenado` with a `dano_por_turno` effect for 3 turns
- **THEN** the condition is added to the character's active conditions with that effect and duration

#### Scenario: Damage-over-time ticks each turn

- **WHEN** a turn begins and the character has an active `dano_por_turno` condition
- **THEN** the system subtracts that condition's per-turn hit-point loss from `pv_actual`

#### Scenario: Turn-count condition expires

- **WHEN** an active condition with a turn-count duration reaches the end of its last turn
- **THEN** the system removes the condition from the character

#### Scenario: Narrator clears a condition

- **WHEN** the narrator declares that an active condition is removed (e.g. the poison is cured)
- **THEN** the condition is removed from the character's active conditions

### Requirement: Death by direct game-over at zero HP

When the character's `pv_actual` reaches 0, the partida SHALL end immediately, reusing the existing finished-game path: the partida state SHALL become finished with a failure ending and a recorded reason. There SHALL be no death-saving throw and no downed-but-not-out intermediate state.

#### Scenario: Reaching zero HP ends the game in failure

- **WHEN** applying damage (or a damage-over-time tick) reduces `pv_actual` to 0
- **THEN** the partida state becomes finished with a failure ending and a recorded reason
- **AND** no further turns can be taken

#### Scenario: No death save is offered

- **WHEN** the character's `pv_actual` reaches 0
- **THEN** the game ends without offering any saving throw or recovery roll

### Requirement: Recovery through rest and inventory potions

The character SHALL regain hit points through narrator-declared rest and through consuming a healing potion held in the inventory. Healing SHALL increase `pv_actual` toward `pv_max` and SHALL NOT exceed `pv_max`. Consuming a potion SHALL remove that potion from the inventory using the existing inventory-removal mechanism. Rest and potion healing SHALL exist as the recovery valve that prevents the failure→damage→disadvantage loop from being a one-way path to death.

#### Scenario: Rest restores hit points

- **WHEN** the narrator declares that the character rests
- **THEN** `pv_actual` increases toward `pv_max` without exceeding it

#### Scenario: Potion heals and is consumed

- **WHEN** the character consumes a healing potion held in the inventory
- **THEN** `pv_actual` increases without exceeding `pv_max`
- **AND** that potion is removed from the inventory

#### Scenario: Healing is capped at max HP

- **WHEN** healing would raise `pv_actual` above `pv_max`
- **THEN** `pv_actual` is set to `pv_max` and not higher

### Requirement: Hit points and conditions surfaced to the player

The system SHALL surface the character's current and maximum hit points and the list of active conditions to the player. When a turn applies damage, the player SHALL be shown that a cost was paid this turn.

#### Scenario: Health is displayed

- **WHEN** the game state is displayed
- **THEN** the player sees `pv_actual` and `pv_max` and any active conditions

#### Scenario: Damage taken this turn is visible

- **WHEN** a turn applies damage to the character
- **THEN** the player is shown that hit points were lost this turn
