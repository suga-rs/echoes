## ADDED Requirements

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
