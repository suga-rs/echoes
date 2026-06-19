# narrative-arc

## Purpose

Drives partida pacing and endings by dramatic structure rather than turn count. A
partida runs for unlimited turns, the narrator tracks a narrative arc (phase and
tension) and a rolling story-so-far summary, decides when the adventure ends, and
generates situation-driven action options each turn.

## Requirements

### Requirement: Unlimited turns

The system SHALL allow a partida to advance for an unlimited number of turns. There SHALL be no hard or soft turn ceiling that ends or blocks a partida, and no turn-count error.

#### Scenario: Advancing past the former limit

- **WHEN** a player advances a partida that is `en_curso` beyond what was previously the maximum turn count
- **THEN** the turn proceeds normally and the system never raises a turn-limit error

#### Scenario: A partida only ends narratively

- **WHEN** a partida is `en_curso` and the narrator has not declared the adventure finished
- **THEN** the partida remains playable regardless of how many turns have elapsed

### Requirement: Narrative arc drives pacing

The system SHALL persist a narrative arc per partida consisting of a phase (`introduccion`, `desarrollo`, `climax`, `resolucion`) and a tension level (integer 0–10). On each turn the narrator SHALL set the phase and tension, and the prompt SHALL feed the current values back so pacing is driven by dramatic structure rather than turn count.

#### Scenario: Arc state is fed back each turn

- **WHEN** a turn is generated
- **THEN** the LLM response includes the current `fase_narrativa` and `tension`, and these are persisted in the partida's world state

#### Scenario: Arc state seeds the next prompt

- **WHEN** the next turn prompt is built
- **THEN** it includes the partida's current `fase_narrativa` and `tension` as context for the narrator

#### Scenario: New game starts in the opening phase

- **WHEN** a partida is created
- **THEN** its world state initializes `fase_narrativa` to `introduccion` and `tension` to a low value

#### Scenario: Backward compatibility for existing partidas

- **WHEN** a partida persisted before this change (without arc fields) is loaded
- **THEN** it deserializes with safe defaults (`introduccion`, low tension) and remains playable

### Requirement: Rolling story summary for long-game consistency

The system SHALL maintain a rolling story-so-far summary (`resumen_historia`) per partida that the narrator updates each turn. The turn prompt SHALL include this summary in place of an unbounded raw event list, so consistency is preserved as games grow long.

#### Scenario: Summary is updated and persisted each turn

- **WHEN** a turn is generated
- **THEN** the LLM response includes an updated `resumen_historia` that is persisted in the partida's world state

#### Scenario: Summary feeds the next prompt

- **WHEN** the next turn prompt is built
- **THEN** it includes the current `resumen_historia` as the narrator's memory of prior events

### Requirement: Narrator-driven endings

The narrator SHALL be able to end a partida by setting `estado_aventura.tipo = "finalizada"` with a `final` of `exito` (objective won), `fracaso` (player died, was captured, or closed off the objective), or `ambiguo` (voluntary or poetic close), plus a `razon_fin`. Endings SHALL be driven by narrative outcome — reaching `resolucion` or a terminal player choice — not by a turn count.

#### Scenario: Player wins the objective

- **WHEN** the player's action achieves the declared objective
- **THEN** the narrator finalizes the partida with `final = exito` and a `razon_fin`, and the partida's persisted state becomes `finalizada`

#### Scenario: Player makes a terminal choice and dies or loses the objective

- **WHEN** the player makes a clearly terminal choice (e.g. fatal action, irrecoverable loss of the objective)
- **THEN** the narrator finalizes the partida with `final = fracaso` and a `razon_fin`

#### Scenario: Finished partida rejects further turns

- **WHEN** a player tries to advance a partida whose state is `finalizada`
- **THEN** the system rejects the action with a "partida already finished" error

#### Scenario: Terminal outcomes are foreshadowed

- **WHEN** a turn presents a choice that can lead to a terminal outcome
- **THEN** the narrative telegraphs the stakes so a resulting death or loss is earned rather than arbitrary

### Requirement: Situation-driven action options

The system SHALL generate exactly three action options per turn that are meaningfully different in intent and arise from the current situation. The system SHALL NOT impose a fixed per-turn set of predetermined action archetypes.

#### Scenario: Options reflect the scene

- **WHEN** a turn is generated
- **THEN** the three options have distinct intentions appropriate to the current scene, rather than following a forced archetype sequence

#### Scenario: Impossible player actions stay in-fiction

- **WHEN** the player's submitted action is impossible given the situation
- **THEN** the narrator narrates the failed attempt without breaking immersion, instead of refusing out-of-fiction
