# turn-image-affordance

## Purpose

The on-demand image control for a turn: a compact icon-button in the turn card's
header row (shown only for turns without an image), and the feedback states
(loading, success, error, limit reached) that accompany generating a scene image.

## Requirements

### Requirement: On-demand image control in the turn header

For a turn that has no image yet, the system SHALL present the on-demand image
control as a compact icon-button in the turn card's header row (alongside the
turn's other header controls), with an accessible label/tooltip describing its
purpose. The system SHALL NOT render an empty placeholder area in place of the
missing image.

#### Scenario: Image-less turn shows header control, no empty slot

- **WHEN** a turn without an image is displayed
- **THEN** a compact image control appears in the turn card header and no empty image placeholder area is shown above the narrative

#### Scenario: Turn with image shows the image, not the control

- **WHEN** a turn already has an image
- **THEN** the image is shown and the on-demand image control is not rendered for that turn

### Requirement: Generation feedback preserved

When the player activates the on-demand image control, the system SHALL show a
loading indicator in the image area while generating, replace it with the image
on success, surface an error message on failure, and show the limit-reached
message when the per-game image cap is exceeded.

#### Scenario: Generating shows loading then image

- **WHEN** the player activates the image control and generation succeeds
- **THEN** a loading indicator is shown in the image area and is replaced by the generated image

#### Scenario: Generation failure surfaces an error

- **WHEN** the player activates the image control and generation fails
- **THEN** an error message is shown and the control remains available to retry

#### Scenario: Limit reached

- **WHEN** the player activates the image control but the game's image cap is exceeded
- **THEN** the limit-reached message is shown instead of an error
