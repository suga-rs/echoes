# character-sheet

## Purpose

Gives each character a six-attribute D&D-style stat block (the six classic abilities, scores 3–18) that backs skill-check resolution. Modifiers are derived with the standard formula, legacy partidas deserialize with safe neutral defaults, and the stat block is surfaced in the UI.

## Requirements

### Requirement: Six-attribute stat block on the character

Each character SHALL carry the six classic D&D abilities — `fuerza`, `destreza`, `constitucion`, `inteligencia`, `sabiduria`, `carisma` — as integer scores in the range 3–18. The stat block SHALL be persisted as part of the character on the partida.

#### Scenario: Scores are within range

- **WHEN** a character's stat block is created
- **THEN** each of the six abilities holds an integer score between 3 and 18 inclusive

#### Scenario: Stat block persists with the partida

- **WHEN** a partida is saved and later reloaded
- **THEN** the character's six ability scores are recovered unchanged

### Requirement: Standard ability modifier

The system SHALL derive each ability's modifier as `floor((score − 10) / 2)`. The modifier SHALL be used when resolving a check that names that ability.

#### Scenario: Modifier from a score

- **WHEN** a character has `destreza` 16
- **THEN** the derived destreza modifier is +3

#### Scenario: Below-average score yields a negative modifier

- **WHEN** a character has `fuerza` 7
- **THEN** the derived fuerza modifier is −2

### Requirement: Backward-compatible defaults for legacy partidas

A partida persisted before this change (without a stat block) SHALL deserialize with safe default scores so it remains playable. The default SHALL be the neutral score 10 for all six abilities (modifier +0).

#### Scenario: Legacy partida loads with neutral stats

- **WHEN** a partida created before this change is loaded
- **THEN** its character deserializes with all six abilities at 10 and a +0 modifier each, and the partida remains playable

### Requirement: Stat block surfaced in the UI

The UI SHALL display the character's six ability scores and their modifiers as part of the visible character information.

#### Scenario: Player views the character sheet

- **WHEN** the player views their character
- **THEN** the six abilities are shown with their scores and derived modifiers
