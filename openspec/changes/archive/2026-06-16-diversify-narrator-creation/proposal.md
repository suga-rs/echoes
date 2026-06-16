## Why

`gpt-4.1-mini` collapses to the same attractor every new game: the same hero names (e.g. "Elias"), the same premises, and the same tone. The per-call sampling controls already in place (`temperature 0.8`, `top_p 0.95`, `frequency_penalty 0.3`, `presence_penalty 0.1`) cannot fix this, because they only diversify *within* one completion — every new game is an independent call with a near-identical input, so the model returns to the same prior. Creation is the single chokepoint: the name, objective, location, premise, and tone chosen there are persisted and re-injected into every later turn, so the whole game inherits creation's sameness. The only lever that moves a model off a cross-call attractor is making the inputs differ.

## What Changes

- Add per-game **curated creative seeds** sampled server-side at creation: a name, premise, tone, and opening-situation drawn from genre-keyed pools and injected into the creation prompt as *inspiration to riff on* (not literal values to copy).
- Add two **optional player inputs** at game start — a free-text *premise* and *tone* — surfaced in the UI under a collapsible "Opciones avanzadas". When provided, they are honored faithfully; when omitted, the sampled seed fills the gap.
- Establish **source-aware framing** in the creation prompt: player-provided fields are framed as instructions to deliver; seed fields are framed as inspiration to reinterpret. Player input always takes precedence over the seed (including the existing "name in description wins" behavior).
- Surface **`prompt_version` in the partidas list** (API + UI). Legacy partidas with a null `prompt_version` are normalized to `1.0.0` for display.
- Bump `PROMPT_VERSION` because the creation contract (prompt inputs) changes.
- Turns are explicitly **out of scope** — the rigid arc skeleton in `SYSTEM_PROMPT_TURNO` stays unchanged to preserve coherence.

## Capabilities

### New Capabilities
- `narrative-creation`: Diversity of the game-creation phase — curated per-game seeds, optional player premise/tone overrides with source-aware precedence, and surfacing of the creation contract version (`prompt_version`).

### Modified Capabilities
<!-- None: the partidas-list and prompt-version surfacing are owned by the new narrative-creation capability since prompt_version is the creation contract version. -->

## Impact

- **Backend**
  - `app/services/prompts.py`: new `CREATION_POOLS`, `SemillaCreativa`, `sample_seed`; `build_creacion_user_prompt` gains `seed`, optional `premisa`/`tono` params and source-aware bucketed rendering; `PROMPT_VERSION` bump.
  - `app/services/partida_service.py`: `crear_partida` samples a seed and threads `premisa`/`tono` into the builder.
  - `app/models/domain.py`: `StartPartidaRequest` gains optional `premisa`/`tono` (length-capped); `PartidaResumen` gains `prompt_version` (null → `1.0.0`).
  - `app/api/partidas.py`: pass `premisa`/`tono` through to the service.
  - `app/repositories/partida_repo.py`: `list_all` query selects `c.metadata.prompt_version`.
- **Frontend**
  - `components/inicio-dialog.tsx`: collapsible "Opciones avanzadas" with premise + tone inputs.
  - `components/partidas-list.tsx`: display `prompt_version` per partida.
  - `lib/api.ts`, `lib/types.ts`: extend the start payload and resumen type (or `pnpm gen:types`).
- **Tests**: seed sampler determinism (injected RNG), prompt contains seed / honors player overrides, name precedence, `prompt_version` normalization in the list.
- **No infra/dependency changes.** Pools are hardcoded in `prompts.py` (versioned with the prompt; no live-config system).
