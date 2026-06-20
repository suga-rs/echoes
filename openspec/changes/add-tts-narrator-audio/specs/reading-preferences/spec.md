## MODIFIED Requirements

### Requirement: Settings surface for appearance

The system SHALL provide a settings surface, opened from a control in the header,
that lets the player adjust appearance preferences (narrator font, narrator text
size, and theme) and the narrator voice preference from a single place.

#### Scenario: Open settings

- **WHEN** the player activates the settings control in the header
- **THEN** a settings panel opens showing controls for narrator font, narrator text size, theme, and narrator voice

#### Scenario: Theme control lives in settings

- **WHEN** the player opens the settings panel
- **THEN** the theme control is available there and is not duplicated as a separate header toggle

## ADDED Requirements

### Requirement: Narrator voice preference

The system SHALL let the player choose the narrator voice used for spoken
narration from the voices offered by the text-to-speech model, with a sensible
default selected when the player has never chosen one. The selected voice SHALL be
used for narration audio.

#### Scenario: Default voice

- **WHEN** the player has never changed the voice preference
- **THEN** a default voice is selected in the settings panel

#### Scenario: Select a voice

- **WHEN** the player selects a different narrator voice in the settings panel
- **THEN** that voice becomes the active preference used for subsequent narration audio

### Requirement: Voice preference persists across sessions

The system SHALL persist the player's narrator voice preference locally so it
survives a page reload, and SHALL apply the stored preference on load.

#### Scenario: Voice preference survives reload

- **WHEN** the player selects a narrator voice and then reloads the app
- **THEN** the settings panel shows the previously chosen voice and narration uses it
