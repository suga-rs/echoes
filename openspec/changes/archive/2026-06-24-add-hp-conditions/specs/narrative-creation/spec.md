## ADDED Requirements

### Requirement: Creation derives the character's hit points

At creation the system SHALL derive the character's maximum hit-point pool (`pv_max`) from the generated Constitución score and SHALL start the character at full health (`pv_actual` equal to `pv_max`) with no active conditions. The derivation SHALL be owned by the system and SHALL NOT be a value supplied by the narrator. The hit points SHALL be persisted on the partida's character alongside the ability scores.

#### Scenario: Hit points derived at creation

- **WHEN** a new game is created and the character's Constitución score is generated
- **THEN** the system derives `pv_max` from that Constitución score
- **AND** sets `pv_actual` equal to `pv_max` with no active conditions

#### Scenario: Narrator does not supply hit points

- **WHEN** the creation response is produced
- **THEN** it contains no narrator-supplied numeric hit-point value
- **AND** `pv_max` is computed by the system from Constitución
