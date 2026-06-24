## MODIFIED Requirements

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
