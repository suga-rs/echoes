# dice-appearance

## Purpose

Player-controlled visual appearance of the 3D d20 — a choice of color scheme
(body color, number-label color, surface finish) selectable from at least three
options, persisted locally and applied across sessions. The per-result semantic
glow stays fixed so the roll outcome reads the same regardless of scheme.

## Requirements

### Requirement: Dice color scheme preference

The system SHALL let the player choose the 3D d20 color scheme from at least three
options: **Marfil** (default), **Obsidiana**, and **Esmeralda**. Each scheme MUST
define the dice body color, the number-label color, and the surface finish
(metalness/roughness). The chosen scheme MUST be applied to the rendered d20.

#### Scenario: Default scheme

- **WHEN** the player has never changed the dice color preference
- **THEN** the d20 renders with the Marfil scheme (pale-gray body, dark numbers)

#### Scenario: Select a different scheme

- **WHEN** the player selects the Obsidiana or Esmeralda scheme
- **THEN** the next time the dice is shown, its body color, number color, and finish
  match the selected scheme

### Requirement: Result glow stays semantic

The per-result emissive glow of the d20 SHALL remain fixed and MUST NOT be altered
by the selected color scheme. The glow colors are gold for critical success, emerald
for success, gray for failure, and red for critical failure, so the roll outcome
reads the same regardless of the chosen scheme.

#### Scenario: Glow unchanged across schemes

- **WHEN** the player changes the dice color scheme
- **THEN** the result glow for a given outcome keeps the same color and meaning as
  with any other scheme

#### Scenario: Numbers stay legible

- **WHEN** any scheme is applied
- **THEN** the number labels contrast against that scheme's body color and remain
  readable

### Requirement: Dice scheme preference persists across sessions

The system SHALL persist the player's dice color scheme locally so it survives a
page reload, and SHALL apply the stored scheme the next time the dice is shown.

#### Scenario: Preference survives reload

- **WHEN** the player selects a non-default scheme and then reloads the app
- **THEN** the d20 renders with the previously chosen scheme
