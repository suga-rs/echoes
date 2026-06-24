## MODIFIED Requirements

### Requirement: Animated 3D dice roll presentation

When a check is resolved, the system SHALL present the roll as a 3D dice animation that settles on the face matching the server-rolled d20 value. The animation SHALL be presentation only: the displayed face, modifier, total, and result tier SHALL always equal the authoritative server result, and the animation SHALL never determine the outcome. The faces of the die SHALL be labelled with their numeric values (1–20) such that the face the die settles on visibly shows the server-rolled value.

The roll SHALL be player-initiated: when the modal opens, the die SHALL rest centered showing the face for the value 20 and SHALL NOT animate until the player activates it (a click or activation on the die or its area). On activation, the die SHALL play the tumble and settle to the server-rolled face, and the reveal SHALL be staged — the d20 result, then the applied modifier, then the total, then the comparison to the DC, then the verdict. Activating the die always plays the animation, including when the environment requests reduced motion.

The dice modal SHALL remain open until the player dismisses it — via a dedicated close control in the top-right of the modal, or by activating outside the modal. The system SHALL NOT auto-dismiss the modal after the die settles.

The outcome narration SHALL NOT be revealed in the narrator while the dice modal is open. The narration received over SSE SHALL be buffered and revealed only after the player dismisses the modal. If the narration has fully arrived by the time the modal is dismissed, it SHALL be revealed as a typewriter reveal; if it is still streaming when the modal is dismissed, it SHALL be revealed live from that point and continue until it completes. The system SHALL provide a non-animated static reveal that conveys the same values (ability, band/DC, d20, modifier, total, result tier) when the 3D animation component is unavailable.

#### Scenario: Faces show their numeric value

- **WHEN** the die settles on the server-rolled value
- **THEN** the face oriented toward the viewer displays that numeric value

#### Scenario: Die waits for the player to roll

- **WHEN** the dice modal opens for a resolved check
- **THEN** the die rests centered showing face 20 and does not animate
- **AND** no roll animation plays until the player activates the die or its area

#### Scenario: Activation plays the roll and settles on the server result

- **WHEN** the player activates the die for a check whose server-rolled value is 14
- **THEN** the die tumbles and comes to rest showing face 14
- **AND** the revealed value, modifier, total, and result tier match the server result exactly

#### Scenario: Staged reveal of the resolution

- **WHEN** the die settles after activation
- **THEN** the d20 value, the applied modifier, the total, the DC comparison, and the verdict are revealed in sequence

#### Scenario: Critical results are visually distinct

- **WHEN** the result tier is `exito_critico` or `fracaso_critico`
- **THEN** the die's presentation is visually distinguished from an ordinary success or failure

#### Scenario: Modal stays open until dismissed

- **WHEN** the die has settled and the resolution is revealed
- **THEN** the modal remains open and is not auto-dismissed
- **AND** it closes only when the player uses the close control or activates outside the modal

#### Scenario: Narration is withheld until dismissal, then replayed

- **WHEN** the phase-2 narration has fully arrived over SSE while the modal is still open
- **THEN** the narrator shows nothing until the player dismisses the modal
- **AND** on dismissal the narration is revealed as a typewriter reveal

#### Scenario: Narration continues live when dismissed early

- **WHEN** the player dismisses the modal before the phase-2 narration finishes streaming
- **THEN** the narration is revealed live from that point and continues until it completes

#### Scenario: Activation animates even under reduced motion

- **WHEN** the player's environment requests reduced motion and the player activates the die
- **THEN** the roll animation plays
