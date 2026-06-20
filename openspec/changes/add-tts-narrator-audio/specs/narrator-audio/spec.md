## ADDED Requirements

### Requirement: Audio playback control on the narrator card

The system SHALL present an audio playback control anchored at the bottom-left of
each narrator (turn) card, with an accessible label/tooltip describing its
purpose. The control SHALL let the player start playback of that turn's narration
and stop/pause it again.

#### Scenario: Play control is shown on the narrator card

- **WHEN** a turn's narrator card is displayed
- **THEN** an audio playback control appears at the bottom-left of that card with an accessible label

#### Scenario: Toggle between play and stop

- **WHEN** the player activates the control while audio for that turn is playing
- **THEN** playback stops/pauses and the control returns to its play state

### Requirement: Lazy audio generation

The system SHALL NOT call the text-to-speech model for a turn until the player
activates that turn's play control. No audio SHALL be generated at turn time,
on page load, or eagerly for turns the player has not requested.

#### Scenario: No audio request before play

- **WHEN** a turn is rendered but the player has not activated its play control
- **THEN** no text-to-speech request is made for that turn

#### Scenario: Audio requested on first play

- **WHEN** the player activates a turn's play control for the first time
- **THEN** the system requests synthesized audio for that turn's narration and begins playback when it is ready

#### Scenario: Replay reuses cached audio

- **WHEN** the player activates the play control again for a turn whose audio was already generated with the same voice (in the current session or in a previous one)
- **THEN** the cached audio is played without re-synthesizing it with the text-to-speech model

### Requirement: Audio reflects the selected voice

The system SHALL synthesize narration using the player's currently selected
narrator voice preference. When the player changes the voice and then plays a
turn, the new audio SHALL use the newly selected voice.

#### Scenario: Selected voice is used

- **WHEN** the player has a narrator voice selected and plays a turn for the first time
- **THEN** the synthesized audio uses that voice

#### Scenario: Voice change applies to new playback

- **WHEN** the player changes the narrator voice and then plays a turn
- **THEN** the audio is (re)synthesized with the newly selected voice

### Requirement: Playback feedback states

While audio for a turn is being generated, the system SHALL show a loading/busy
indication on that turn's control, transition to a playing state once audio
begins, and surface an error message on failure while leaving the control
available to retry.

#### Scenario: Loading then playing

- **WHEN** the player activates the play control and generation succeeds
- **THEN** a busy indication is shown while generating and the control transitions to the playing state when audio begins

#### Scenario: Generation failure surfaces an error

- **WHEN** the player activates the play control and audio generation fails
- **THEN** an error message is shown and the control remains available to retry

### Requirement: Narration audio is always in Spanish

The system SHALL always synthesize narration audio in Spanish, consistent with the
`spanish-output-contract` that pins the narrator text to Spanish. The spoken
language SHALL be Spanish regardless of which voice the player has selected; the
voice preference SHALL affect only the voice, never the language.

#### Scenario: Audio is Spanish for any voice

- **WHEN** the player plays a turn with any selected voice
- **THEN** the resulting audio narrates the turn's text in Spanish

### Requirement: Generated audio is cached in Blob Storage

The system SHALL cache synthesized narration audio in Blob Storage, keyed by the
game, turn, and voice. On a request for which a cached clip for that turn + voice
already exists, the system SHALL return the cached audio without calling the
text-to-speech model. A given turn + voice SHALL be synthesized at most once.
Audio for a game SHALL be removed when the game is deleted.

#### Scenario: Cache miss synthesizes and stores

- **WHEN** the client requests audio for a turn + voice that has no cached clip
- **THEN** the system synthesizes the audio, stores it in Blob Storage, and returns it

#### Scenario: Cache hit avoids re-synthesis

- **WHEN** the client requests audio for a turn + voice that already has a cached clip
- **THEN** the system returns the cached clip and does not call the text-to-speech model

#### Scenario: Different voice is a separate cache entry

- **WHEN** the client requests audio for a turn with a voice different from one already cached for that turn
- **THEN** the system synthesizes and stores a separate clip for the new voice, leaving the existing one intact

#### Scenario: Audio removed with the game

- **WHEN** a game is deleted
- **THEN** the audio clips cached for that game are removed from Blob Storage

### Requirement: Backend on-demand audio endpoint

The backend SHALL expose an endpoint that returns the audio for a specified turn's
narration using the requested voice — serving the cached clip when present and
otherwise synthesizing it with the text-to-speech deployment, storing it, and
returning a reference to it. The endpoint SHALL validate that the turn exists for
the game, SHALL reject an unsupported voice, and SHALL return an error when
synthesis fails.

#### Scenario: Returns audio for a turn

- **WHEN** the client requests audio for an existing turn of a game with a valid voice
- **THEN** the backend returns a reference to that turn's audio (cached or freshly synthesized) in the requested voice

#### Scenario: Unknown turn rejected

- **WHEN** the client requests audio for a turn that does not exist in the game
- **THEN** the backend returns a not-found error and does not call the text-to-speech model

#### Scenario: Unsupported voice rejected

- **WHEN** the client requests audio with a voice that is not supported
- **THEN** the backend returns an error and does not call the text-to-speech model
