## ADDED Requirements

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

The system SHALL resolve a declared check by rolling a single real d20 server-side, adding the relevant ability modifier, and comparing the total against the band's DC. A natural 20 SHALL always be a critical success and a natural 1 SHALL always be a critical failure, independent of the modifier and DC. Otherwise, total ≥ DC SHALL be a success and total < DC SHALL be a failure. The roll SHALL use a randomness source that is injectable so resolution is deterministic under test.

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

#### Scenario: Deterministic roll under test

- **WHEN** the roller is given a seeded randomness source
- **THEN** it returns the same d20 value for the same seed

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

When a check is resolved, the system SHALL present the roll as a 3D dice animation that settles on the face matching the server-rolled d20 value. The animation SHALL be presentation only: the displayed face, modifier, total, and result tier SHALL always equal the authoritative server result, and the animation SHALL never determine the outcome. The reveal SHALL be staged — the d20 result, then the applied modifier, then the total, then the comparison to the DC, then the verdict. The system SHALL provide a non-animated fallback that conveys the same values when the animation is unavailable or unwanted.

#### Scenario: Animation settles on the server result

- **WHEN** the server rolls a d20 value of 14 for a check
- **THEN** the 3D die animation comes to rest showing face 14
- **AND** the revealed value, modifier, total, and result tier match the server result exactly

#### Scenario: Staged reveal of the resolution

- **WHEN** the die settles
- **THEN** the d20 value, the applied modifier, the total, the DC comparison, and the verdict are revealed in sequence

#### Scenario: Critical results are visually distinct

- **WHEN** the result tier is `exito_critico` or `fracaso_critico`
- **THEN** the die's presentation is visually distinguished (e.g. a critical-success and a critical-failure treatment) from an ordinary success or failure

#### Scenario: Reduced-motion fallback

- **WHEN** the player's environment requests reduced motion, or the animation component is unavailable
- **THEN** the resolution is shown as a static element conveying ability, band/DC, d20, modifier, total, and result tier, with no animation

#### Scenario: Animation overlaps phase-2 latency

- **WHEN** a check resolves and the phase-2 narration call is in flight
- **THEN** the dice animation plays during that wait and the narration appears as or after the animation completes
