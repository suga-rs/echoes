# npc-visual-consistency

## Purpose

Mantener la apariencia de los NPCs y enemigos consistente entre las imágenes de una misma partida, anclándolos a una descripción visual canónica de texto reutilizada en cada escena donde el NPC está presente, sin agregar generaciones de imagen ni tiempo de render por turno.

## Requirements

### Requirement: Canonical NPC visual description

The system SHALL capture and persist a canonical visual description (in English) for each NPC at the moment it is first introduced, analogous to the protagonist's visual description. The description SHALL be stored exactly once per NPC and reused unchanged on every later turn; it SHALL NOT be regenerated or overwritten on subsequent turns.

#### Scenario: Visual description captured on NPC introduction
- **WHEN** the narrator introduces a new NPC for the first time in a turn
- **THEN** the system persists that NPC's canonical English visual description alongside its name, narrative description, and attitude

#### Scenario: Visual description is stable across turns
- **WHEN** an already-introduced NPC appears again in a later turn
- **THEN** the system keeps the NPC's originally stored visual description and does not replace it with new text

#### Scenario: Pre-existing NPC without visual description
- **WHEN** a game created before this capability has NPCs without a stored visual description
- **THEN** the system treats the missing description as absent and generates images without anchoring that NPC, without error

### Requirement: NPC presence declared per scene

The system SHALL allow the narrator to declare, in the scene-image block of each turn, which already-known NPCs are visually present in that turn's scene, by referencing their existing names.

#### Scenario: Narrator lists present NPCs
- **WHEN** the narrator produces a turn whose scene includes one or more known NPCs
- **THEN** the turn's image block includes the list of those NPCs' names

#### Scenario: No NPCs present
- **WHEN** the narrator produces a turn whose scene includes no NPCs
- **THEN** the turn's image block declares an empty presence list and the image is generated from the protagonist and scene only

### Requirement: Scene images anchored to present NPCs

The system SHALL inject the canonical visual descriptions of the declared-present NPCs into the scene-image prompt, alongside the protagonist's description, so each NPC's appearance is driven by its stored description rather than re-invented per image. The protagonist SHALL continue to be anchored by the existing reference-image flow; NPC anchoring is text-only and SHALL NOT add image generations or change the image-generation mechanism.

#### Scenario: Present NPC appearance comes from canonical description
- **WHEN** a scene image is generated for a turn that declares present NPCs which have stored visual descriptions
- **THEN** the system builds the image prompt including those NPCs' canonical visual descriptions
- **AND** does not generate any additional image and does not change the per-game image counter beyond the single scene image

#### Scenario: Anchoring count is bounded
- **WHEN** the number of declared-present NPCs with visual descriptions exceeds the per-image anchoring limit
- **THEN** the system anchors at most the limit and omits the rest from the prompt

### Requirement: Resilient name resolution

The system SHALL resolve declared NPC names tolerantly against persisted NPCs and SHALL degrade gracefully: a declared name that does not resolve to a known NPC with a stored visual description SHALL be ignored, and the scene image SHALL still be generated.

#### Scenario: Unknown or hallucinated NPC name
- **WHEN** the narrator declares a present NPC name that does not match any persisted NPC
- **THEN** the system ignores that name and generates the scene image without anchoring it

#### Scenario: Name resolves despite minor differences
- **WHEN** a declared name differs only by case or surrounding whitespace from a persisted NPC name
- **THEN** the system resolves it to that NPC and uses its canonical visual description
