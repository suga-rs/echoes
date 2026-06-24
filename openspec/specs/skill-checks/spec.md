# skill-checks

## Purpose

Resolves uncertain player actions through real, server-side d20 skill checks driven by the narrator. The narrator declares a check (one ability, one difficulty band) without authoring the outcome; the system owns the band-to-DC mapping, rolls a real d20, applies the relevant ability modifier, and the narrator narrates the result in a constrained second phase. Resolved checks are persisted and surfaced transparently to the player, presented as a 3D dice animation that settles on the authoritative server value.

## Requirements

### Requirement: Narrator declares checks, never raw difficulty

When a player's action has an uncertain outcome, the narrator SHALL declare a check rather than authoring the result. A declared check SHALL name exactly one of the six abilities (`fuerza`, `destreza`, `constitucion`, `inteligencia`, `sabiduria`, `carisma`) and exactly one difficulty band (`trivial`, `facil`, `media`, `dificil`, `heroica`). The narrator SHALL NOT supply a numeric DC; the system owns the band-to-DC mapping. When the narrator judges the action trivial (guaranteed) or impossible, it SHALL NOT declare a check and the turn SHALL resolve in a single narration as before.

#### Scenario: Uncertain action triggers a declared check

- **WHEN** the player submits an action whose outcome the narrator judges uncertain
- **THEN** the phase-1 LLM response declares a check naming one ability and one difficulty band
- **AND** it does not include a numeric DC

#### Scenario: Trivial or impossible action skips the check

- **WHEN** the player's action is guaranteed to succeed or impossible given the situation
- **THEN** no check is declared and the turn is narrated in a single call without a roll

#### Scenario: Invalid ability or band is rejected and retried

- **WHEN** the narrator declares a check with an ability or band outside the allowed enums
- **THEN** the response fails schema validation and the existing one-retry path feeds the error back before raising

### Requirement: Fixed difficulty bands map to DCs

The system SHALL own a fixed mapping from difficulty band to DC: `trivial` = 5, `facil` = 10, `media` = 15, `dificil` = 20, `heroica` = 25. The DC for a check SHALL be derived solely from the declared band; the narrator's input never overrides it.

#### Scenario: Band resolves to its DC

- **WHEN** the narrator declares a check with band `media`
- **THEN** the system uses DC 15 for that check regardless of any other model output

### Requirement: Real server-side d20 resolution

The system SHALL resolve a declared check by rolling a real d20 server-side, adding the relevant ability modifier, and comparing the total against the band's DC. When the character has an active condition that grants `desventaja` on the relevant roll, the system SHALL roll two d20s and use the **worse** (lower) of the two as the d20 value for the check; otherwise it SHALL roll a single d20. A natural 20 SHALL always be a critical success and a natural 1 SHALL always be a critical failure, independent of the modifier and DC; under disadvantage the natural value evaluated for the crit rule SHALL be the kept (worse) die. Otherwise, total ≥ DC SHALL be a success and total < DC SHALL be a failure. The roll SHALL use a randomness source that is injectable so resolution is deterministic under test.

#### Scenario: Total meets or beats the DC

- **WHEN** a d20 roll of 11 is made for a `destreza` check at DC 15 with a destreza modifier of +4
- **THEN** the total is 15, the result tier is `exito`, and the narrator narrates a success

#### Scenario: Total falls short of the DC

- **WHEN** a d20 roll of 6 is made for a check at DC 15 with a modifier of +2
- **THEN** the total is 8, the result tier is `fracaso`, and the narrator narrates a failure

#### Scenario: Natural 20 is always a critical success

- **WHEN** the d20 shows a natural 20 for a check at DC 25 with a negative modifier
- **THEN** the result tier is `exito_critico` regardless of the total

#### Scenario: Natural 1 is always a critical failure

- **WHEN** the d20 shows a natural 1 for a check at DC 5 with a high modifier
- **THEN** the result tier is `fracaso_critico` regardless of the total

#### Scenario: Disadvantage keeps the worse of two d20s

- **WHEN** the character has an active condition granting `desventaja` and the two rolled d20s are 14 and 6
- **THEN** the check uses 6 as the d20 value
- **AND** the crit rule is evaluated against the kept value 6

#### Scenario: No disadvantage rolls a single d20

- **WHEN** the character has no condition granting `desventaja` on the relevant roll
- **THEN** the system rolls a single d20 for the check

#### Scenario: Deterministic roll under test

- **WHEN** the roller is given a seeded randomness source
- **THEN** it returns the same d20 value (or pair of values under disadvantage) for the same seed

### Requirement: Two-phase turn for checks

A turn that declares a check SHALL be resolved in two LLM calls. Phase 1 SHALL produce the check declaration plus the in-fiction setup of what is at stake. After the system rolls, phase 2 SHALL produce the outcome narration, the three next options, and the state/arc updates, and SHALL be constrained to honor the rolled result tier. The phase-2 prompt SHALL include the declared ability, the DC, the rolled d20, the applied modifier, the total, and the result tier.

#### Scenario: Phase 2 honors a success

- **WHEN** phase 1 declared a check and the roll resolved to `exito` or `exito_critico`
- **THEN** the phase-2 narration depicts the action succeeding, with `exito_critico` adding an extra favorable beat

#### Scenario: Phase 2 honors a failure

- **WHEN** the roll resolved to `fracaso` or `fracaso_critico`
- **THEN** the phase-2 narration depicts the action failing without breaking immersion, with `fracaso_critico` adding an extra adverse complication

#### Scenario: Result tier is persisted on the turn

- **WHEN** a checked turn completes
- **THEN** the turn's history record persists the declared ability, band, DC, d20 value, applied modifier, total, and result tier

### Requirement: Roll transparency to the player

The system SHALL surface the resolved check to the player: the declared ability, the difficulty band and its DC, the rolled d20 value, the applied modifier, the total, and the result tier. Turns with no check SHALL display no roll element.

#### Scenario: Checked turn shows the roll

- **WHEN** a turn that resolved a check is displayed
- **THEN** the player sees the ability, band/DC, d20, modifier, total, and result tier

#### Scenario: Unchecked turn shows no roll

- **WHEN** a turn that declared no check is displayed
- **THEN** no roll element is shown

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
