# spanish-output-contract

## Purpose

Pins the language of every player-facing LLM output field to Spanish rioplatense,
with the `_en` naming suffix as the sole, explicit exception for English fields.
Short label-like fields (`objetivo`, `inventario`, `opciones`) were drifting to
English because the language was asserted globally rather than per-field; this
capability enforces the rule in both system prompts and in the JSON schemas, and
remediates partidas already persisted with English values.

## Requirements

### Requirement: Player-facing LLM text fields are Spanish rioplatense

Every text field the LLM emits that is shown to the player SHALL be in Spanish rioplatense, with the sole exception of fields whose JSON property name ends in `_en`, which SHALL be in English. Both system prompts (creation and turn) SHALL state this rule explicitly and bidirectionally, anchored to the `_en` naming convention. The leaky short fields — `objetivo`, `inventario_inicial`, `agregar_inventario` items, `quitar_inventario` items, and `opciones` — SHALL each carry a JSON-schema `description` reinforcing that they are Spanish rioplatense.

#### Scenario: Short label-like fields come back in Spanish

- **WHEN** the LLM generates a creation response or a turn response
- **THEN** `objetivo`, the `inventario`/`opciones` entries, and any inventory deltas are written in Spanish rioplatense
- **AND** only fields whose name ends in `_en` (`descripcion_visual_en`, `descripcion_escena_en`, `descripcion_imagen_en`) are in English

#### Scenario: Prompt states the rule bidirectionally

- **WHEN** either system prompt is built
- **THEN** it contains an explicit rule that all text fields are Spanish rioplatense except `_en`-suffixed fields, which are English

#### Scenario: Schema descriptions reinforce the leaky fields

- **WHEN** the creation and turn JSON schemas are inspected
- **THEN** `objetivo`, `inventario_inicial`, `agregar_inventario`, `quitar_inventario`, and `opciones` each carry a `description` stating the value is Spanish rioplatense

### Requirement: Prompt contract version reflects the language rule

The system SHALL bump `PROMPT_VERSION` when the language rule is added, so partidas created afterward record the new contract version and quality can be correlated with it.

#### Scenario: New partida records the bumped version

- **WHEN** a partida is created after this change ships
- **THEN** its persisted `prompt_version` is the bumped value, distinct from the prior version

### Requirement: Legacy partidas with English fields are remediated

The system SHALL provide a one-off remediation for partidas persisted before this change whose `objetivo` (and, where present, inventory entries) are in English. The remediation SHALL translate the affected fields into Spanish rioplatense and persist the corrected partida, SHALL be idempotent (safe to re-run, leaving already-Spanish partidas unchanged), and SHALL NOT alter any `_en` field, the narrative history, or any other game state.

#### Scenario: A legacy partida with an English objective is corrected

- **WHEN** the remediation runs over a partida whose persisted `objetivo` is in English
- **THEN** the `objetivo` is rewritten in Spanish rioplatense and the partida is persisted with that value

#### Scenario: Remediation is idempotent

- **WHEN** the remediation runs over a partida whose fields are already Spanish, or runs a second time over an already-corrected partida
- **THEN** the partida is left unchanged

#### Scenario: Remediation preserves untouched state

- **WHEN** the remediation corrects a partida
- **THEN** `_en` fields, the narrative history, world-state structure, and all non-language game state are left exactly as they were
