# character-visual-reference

## Purpose

Keep the protagonist visually consistent across all of a game's images by anchoring scene generation to a single canonical character reference image, instead of re-describing the character in text on every generation.

## Requirements

### Requirement: Canonical character reference image

The system SHALL generate, exactly once per game, a canonical reference image of the protagonist: a full-body portrait on a neutral background rendered in the game's genre style, derived from the character's existing visual description. The reference image URL SHALL be persisted on the character so it survives reloads.

#### Scenario: Reference generated on first image need
- **WHEN** a game needs its first image (creation, turn, on-demand, or final) and the character has no stored reference image
- **THEN** the system generates a full-body neutral-background portrait from the character's visual description in the genre style
- **AND** persists the resulting image URL on the character

#### Scenario: Reference reused on subsequent images
- **WHEN** a game needs any image and the character already has a stored reference image URL
- **THEN** the system reuses the stored reference and does NOT generate a new one

#### Scenario: Reference excluded from the image budget
- **WHEN** the character reference image is generated
- **THEN** the per-game image counter (`imagenes_generadas`) is NOT incremented and the reference does not count against `MAX_IMAGENES_POR_PARTIDA`

### Requirement: Scene images anchored to the reference

The system SHALL produce per-scene images via the image-edit endpoint using the stored character reference image with `input_fidelity="high"`, so the protagonist's identity is held by the reference pixels across all scenes. The scene description SHALL drive composition and the character text SHALL reinforce appearance details.

#### Scenario: Scene image generated from reference
- **WHEN** a scene image is generated for a game that has a stored reference image
- **THEN** the system calls the image-edit endpoint with the reference image, `input_fidelity="high"`, and a prompt combining the character description and the scene description
- **AND** increments the per-game image counter for that scene image

#### Scenario: Scene image still bounded by the cap
- **WHEN** a game has already reached `MAX_IMAGENES_POR_PARTIDA`
- **THEN** no scene image (and no reference) is generated

### Requirement: Reference scope limited to new games

The system SHALL apply the reference-anchored image flow only to games created after this capability ships. Pre-existing games SHALL continue to use the text-only generation path with no migration.

#### Scenario: Pre-existing game keeps text-only path
- **WHEN** a game created before this capability requests an image
- **THEN** the system generates the image from text only and does not require or create a reference image

### Requirement: Resilient reference generation

The system SHALL degrade gracefully if reference generation fails: the scene image SHALL fall back to the text-only path so the game still renders, and reference creation SHALL be retried on the next image request.

#### Scenario: Reference generation fails
- **WHEN** generating the character reference image fails
- **THEN** the system produces the scene image via the text-only path for that request
- **AND** leaves the character without a stored reference so the next image request retries reference creation

### Requirement: Game-start loading state

The frontend SHALL display a loading state during game start that covers the first-image step (reference generation followed by the first scene image), so the interface does not appear frozen while two image generations run back to back.

#### Scenario: Loading state shown during game start
- **WHEN** a new game is starting and its first image is being produced
- **THEN** the frontend shows an explicit loading state until the first turn and its image are ready
