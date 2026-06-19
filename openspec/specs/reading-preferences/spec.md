# reading-preferences

## Purpose

Player-controlled appearance settings for the narrator text (font family incl. a
dyslexia-friendly option, text size) plus theme — surfaced from a single settings
panel, persisted locally, and applied across sessions. The chosen font family is
also shared with the player-facing game-text surfaces.

## Requirements

### Requirement: Settings surface for appearance

The system SHALL provide a settings surface, opened from a control in the header,
that lets the player adjust appearance preferences (narrator font, narrator text
size, and theme) from a single place.

#### Scenario: Open settings

- **WHEN** the player activates the settings control in the header
- **THEN** a settings panel opens showing controls for narrator font, narrator text size, and theme

#### Scenario: Theme control lives in settings

- **WHEN** the player opens the settings panel
- **THEN** the theme control is available there and is not duplicated as a separate header toggle

### Requirement: Narrator font preference

The system SHALL let the player choose the narrator text font from at least three
options: a serif (default), a sans-serif, and a dyslexia-friendly font. The chosen
font MUST be applied to the narrator text.

#### Scenario: Default font

- **WHEN** the player has never changed the font preference
- **THEN** the narrator text renders in the default serif font

#### Scenario: Select dyslexia-friendly font

- **WHEN** the player selects the dyslexia-friendly font option
- **THEN** the narrator text re-renders in that font immediately

#### Scenario: Select sans-serif font

- **WHEN** the player selects the sans-serif font option
- **THEN** the narrator text re-renders in the sans-serif font immediately

### Requirement: Narrator font applied to player-facing game text

The configurable narrator font family SHALL also be applied to the player-facing
narrative game-text surfaces — the player's submitted actions, the suggested
option buttons, the inventory items, the current objective, and the character
description — so their typography matches the narrator text. Only the font family
is shared; the narrator text size preference applies to the narrator text only and
MUST NOT resize these surfaces.

#### Scenario: Font applied to game-text surfaces

- **WHEN** the player selects a non-default narrator font
- **THEN** the player's actions, the option buttons, the inventory items, the
  objective, and the character description re-render in that font, matching the
  narrator text

#### Scenario: Size does not affect game-text surfaces

- **WHEN** the player changes the narrator text size
- **THEN** the player's actions, option buttons, inventory items, objective, and
  character description keep their existing size (only the narrator text resizes)

### Requirement: Narrator text size preference

The system SHALL let the player choose the narrator text size from at least three
levels (small, medium, large). The chosen size MUST be applied to the narrator
text. Medium is the default.

#### Scenario: Default size

- **WHEN** the player has never changed the size preference
- **THEN** the narrator text renders at the medium (default) size

#### Scenario: Change size

- **WHEN** the player selects a different size level
- **THEN** the narrator text re-renders at that size immediately

### Requirement: Preferences persist across sessions

The system SHALL persist the player's font and size preferences locally so they
survive a page reload, and SHALL apply the stored preferences on load before or
as the narrator text is shown.

#### Scenario: Preference survives reload

- **WHEN** the player sets a font and size and then reloads the app
- **THEN** the narrator text renders with the previously chosen font and size

#### Scenario: Applied without flashing the default

- **WHEN** the app loads with a stored non-default preference
- **THEN** the narrator text is shown using the stored preference rather than the default value
