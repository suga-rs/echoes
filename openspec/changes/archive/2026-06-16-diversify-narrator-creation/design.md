## Context

The narrator (`gpt-4.1-mini`) is invoked once per game at creation through `PartidaService.crear_partida` → `build_creacion_user_prompt` → `FoundryClient.chat_json_raw`. That call already runs at `temperature 0.8`, `top_p 0.95`, `frequency_penalty 0.3`, `presence_penalty 0.1`. Despite this, separate games collapse to the same names, premises, and tone.

Root cause: `frequency_penalty`/`presence_penalty` only suppress repetition *within a single completion*; they reset on every call. Each new game is an independent request with a near-identical input (fixed system prompt + a short, often-vague character description), so the model returns to the same prior. Temperature flattens the distribution but a dominant prior survives. The only effective lever is making the *input* differ per game.

Creation is the leverage point: its outputs (`nombre`, `objetivo`, `ubicacion_inicial`, `resumen_historia`) are persisted in `Partida` and re-injected verbatim by `build_turno_user_prompt` on every later turn. Diversifying creation diversifies the whole game without touching the turn loop.

## Goals / Non-Goals

**Goals:**
- Eliminate cross-game sameness in names, premise, and tone by injecting per-game entropy into the creation input.
- Let players optionally steer premise and tone, with their input always taking precedence over generated seeds.
- Keep the default flow (genre + character description) a single, simple decision.
- Surface the creation contract version (`prompt_version`) in the partidas list for auditing, normalizing legacy nulls to `1.0.0`.

**Non-Goals:**
- No changes to the turn loop or the arc skeleton in `SYSTEM_PROMPT_TURNO` (its rigidity is intentional for coherence).
- No live/external configuration system for pools — they are hardcoded and versioned with the prompt.
- No change to image generation, persistence schema migration, or LLM sampling parameters.
- No player control over the opening-situation (`apertura`) — seed-only.

## Decisions

### D1: Curated pools sampled server-side, injected as inspiration
Genre-keyed pools (`CREATION_POOLS: dict[Genero, dict[str, list[str]]]`) hold `nombres`, `premisas`, `tonos`, `aperturas`. A `sample_seed(genero, rng)` returns a `SemillaCreativa` dataclass picking one from each.

- **Why pools over "be more creative" prompting:** instructing a model to "be random/varied" shifts the attractor to its *next* favorite (Elias→Elara); it does not break the determinism. Sampling concrete, differing inputs does.
- **Why four independent dimensions:** combinatorial coverage (~10×12×8×8 ≈ 7,680 combinations) far exceeds the single current attractor; sameness from a small pool is mitigated by multiplicity plus the model *reinterpreting* rather than copying.
- **Alternative rejected — OpenAI `seed` param:** does the opposite (pins determinism).
- **Alternative rejected — raising temperature further:** already at 0.8; cannot fix a cross-call prior and risks degrading the coherence of the visual character description.

### D2: Injected RNG for testability
`sample_seed(genero, rng: random.Random | None = None)`. Production passes nothing (fresh entropy); tests pass `random.Random(42)` for deterministic assertions. Satisfies the test-first mandate without hidden global randomness.

### D3: Source-aware bucketed framing in the builder
`build_creacion_user_prompt(genero, descripcion, seed, premisa=None, tono=None)` sorts each field into one of two rendered buckets:
- **"LO QUE PIDIÓ EL JUGADOR (honralo fielmente)"** — fields the player supplied (`premisa`/`tono` when present).
- **"SEMILLA CREATIVA (inspiración, NO guion)"** — seed fallbacks for the rest, plus `apertura` always, plus the suggested name as a *fallback only*.

A player premise is an instruction to deliver; a seed premise is a spark to riff on — same field, opposite framing. Placement is driven by source, so framing is always correct. Name precedence ("if the player named the character in their description, use that; the suggested name is only a backup") is stated explicitly, extending the existing "respetala fielmente" instruction.

### D4: Player inputs are optional and length-capped
`StartPartidaRequest.premisa: str | None` (max ~200) and `tono: str | None` (max ~100), both defaulting to `None`. Only `descripcion_personaje` stays required (existing 422 behavior unchanged). Caps prevent a player pasting an essay into the system prompt.

### D5: `prompt_version` surfaced and normalized
`PartidaResumen` gains `prompt_version: str`. The `list_all` Cosmos query selects `c.metadata.prompt_version`; legacy documents return null and are normalized to `"1.0.0"` at the DTO boundary (Pydantic validator/default-coercion). Frontend renders it per row. This pairs naturally with the `PROMPT_VERSION` bump this change requires.

### D6: UI under collapsible "Opciones avanzadas"
Premise + tono inputs live in a collapsed section of `inicio-dialog.tsx` so the default path stays genre + description. Discoverable without adding friction for players who don't care.

## Risks / Trade-offs

- **Small pools re-introduce sameness** → four multiplied dimensions + model reinterpretation keep the effective space large; pools can grow later with no architectural change.
- **Model ignores the seed / treats inspiration as literal** → explicit "inspiración, NO guion, no copies literal" framing; reinterpretation is acceptable and still varied even on a repeated draw.
- **Player premise conflicts with genre or character description** → existing system-prompt guidance ("ajustala manteniendo el espíritu") covers reconciliation; player input is honored but harmonized.
- **`PROMPT_VERSION` bump breaks version-correlated telemetry continuity** → intended; the bump is the signal that the creation contract changed.
- **Frontend/backend type drift on the new fields** → regenerate via `pnpm gen:types` against the running backend rather than hand-editing where practical.

## Migration Plan

No data migration. Legacy partidas (null `prompt_version`) display as `1.0.0`; existing games are unaffected at runtime. Rollback is a code revert plus reverting `PROMPT_VERSION`; persisted partidas remain valid either way (new optional fields are additive). Deploy backend and frontend together so the new optional payload fields and the resumen `prompt_version` field line up.

## Open Questions

- None blocking. Pool contents (exact names/premises/tonos per genre) are an implementation detail to be filled during apply.
