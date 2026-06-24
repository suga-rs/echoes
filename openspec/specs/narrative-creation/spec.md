# narrative-creation

## Purpose

Diversifies the game-creation phase so independent games do not collapse to the
same narrator attractor (repeated hero names, premises, and tone). Per-game
creative seeds are sampled server-side from curated genre pools and injected as
inspiration; players may optionally steer the premise and tone, which always take
precedence over the seed. Also surfaces the creation contract version
(`prompt_version`) recorded on each partida.

## Requirements

### Requirement: Per-game creative seeds at creation

The system SHALL sample a creative seed per new game from genre-keyed curated pools and inject it into the creation prompt as inspiration. The seed SHALL include a suggested name, premise, tone, and opening-situation. The sampler SHALL accept an injectable random source so that seeding is deterministic under test.

#### Scenario: Seed sampled for a new game

- **WHEN** a player starts a new game for a given genre
- **THEN** the system samples one name, one premise, one tone, and one opening-situation from that genre's pools
- **AND** injects them into the creation prompt framed as inspiration to reinterpret, not literal values to copy

#### Scenario: Deterministic sampling under test

- **WHEN** `sample_seed` is called with a seeded random source
- **THEN** it returns the same seed for the same seed value and genre

#### Scenario: Two games diverge

- **WHEN** two games are created for the same genre with the same character description
- **THEN** their sampled seeds are drawn independently and the resulting games are not constrained to share name, premise, or tone

### Requirement: Optional player premise and tone overrides

The system SHALL accept an optional player-provided premise and an optional player-provided tone at game start. Both SHALL default to absent. When provided, each SHALL be framed in the creation prompt as an instruction to honor faithfully rather than inspiration. When absent, the corresponding sampled seed value SHALL be used instead. Player-provided values SHALL be length-capped.

#### Scenario: Player provides premise and tone

- **WHEN** a player starts a game and supplies a premise and a tone
- **THEN** the creation prompt presents them as player intent to be honored
- **AND** the sampled seed's premise and tone are not used

#### Scenario: Player omits premise and tone

- **WHEN** a player starts a game without a premise or tone
- **THEN** the sampled seed's premise and tone fill the gap, framed as inspiration

#### Scenario: Overlong player input rejected

- **WHEN** a player supplies a premise or tone exceeding its length cap
- **THEN** the request is rejected with a validation error

#### Scenario: Character description remains the only required creative input

- **WHEN** a player starts a game with only genre and character description
- **THEN** the request is accepted and seeds fill premise, tone, and opening-situation

### Requirement: Player input precedence over seeds

The system SHALL always prefer player-provided creative input over the sampled seed. If the player names their character within the character description, that name SHALL be used and the seed's suggested name SHALL serve only as a fallback when no name is given.

#### Scenario: Player names their character

- **WHEN** the player's character description includes a name
- **THEN** that name is used for the character
- **AND** the seed's suggested name is ignored

#### Scenario: Player gives no name

- **WHEN** the player's character description includes no name
- **THEN** the seed's suggested name is available as a fallback for the narrator

### Requirement: Advanced options surfaced collapsibly in the UI

The new-game UI SHALL expose the optional premise and tone inputs within a collapsible "Opciones avanzadas" section that is collapsed by default, keeping genre and character description as the primary inputs.

#### Scenario: Default new-game view

- **WHEN** a player opens the new-game dialog
- **THEN** genre and character description are shown
- **AND** the premise and tone inputs are hidden inside a collapsed "Opciones avanzadas" section

#### Scenario: Player expands advanced options

- **WHEN** a player expands "Opciones avanzadas"
- **THEN** the premise and tone inputs become available to fill

### Requirement: Creation contract version surfaced in the partidas list

The partidas list SHALL include the `prompt_version` recorded for each partida. Partidas persisted without a `prompt_version` SHALL be presented as version `1.0.0`.

#### Scenario: Partida created under the current contract

- **WHEN** the partidas list is requested
- **THEN** each partida created with a recorded `prompt_version` shows that version

#### Scenario: Legacy partida without a version

- **WHEN** the partidas list includes a partida whose stored `prompt_version` is null
- **THEN** that partida is presented with version `1.0.0`

### Requirement: Creation generates the character's ability scores

The creation contract SHALL additionally produce the six ability scores (`fuerza`, `destreza`, `constitucion`, `inteligencia`, `sabiduria`, `carisma`) for the new character, each an integer in 3–18, derived from the player's character description and the chosen genre so they reflect the described archetype. The narrator SHALL bias the scores toward the description (a described warrior leans high `fuerza`; a scholar leans high `inteligencia`) while keeping every ability within range.

#### Scenario: Scores accompany the new character

- **WHEN** a new game is created
- **THEN** the creation response includes the six ability scores, each an integer between 3 and 18 inclusive
- **AND** they are persisted on the partida's character

#### Scenario: Scores reflect the described archetype

- **WHEN** the player's description depicts a physically powerful brawler
- **THEN** the generated `fuerza` score trends higher than `inteligencia`, while all six remain within 3–18

#### Scenario: Invalid scores are rejected and retried

- **WHEN** the creation response omits an ability or returns a score outside 3–18
- **THEN** the response fails schema validation and the existing one-retry path feeds the error back before raising

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
