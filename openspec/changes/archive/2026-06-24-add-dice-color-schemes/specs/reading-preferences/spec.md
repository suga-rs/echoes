## MODIFIED Requirements

### Requirement: Settings surface for appearance

The system SHALL provide a settings surface, opened from a control in the header,
that lets the player adjust appearance preferences (narrator font, narrator text
size, theme, and dice color scheme) from a single place.

#### Scenario: Open settings

- **WHEN** the player activates the settings control in the header
- **THEN** a settings panel opens showing controls for narrator font, narrator text
  size, theme, and dice color scheme

#### Scenario: Theme control lives in settings

- **WHEN** the player opens the settings panel
- **THEN** the theme control is available there and is not duplicated as a separate header toggle

#### Scenario: Dice color control lives in settings

- **WHEN** the player opens the settings panel
- **THEN** a dice color scheme control is available there alongside the other appearance controls
