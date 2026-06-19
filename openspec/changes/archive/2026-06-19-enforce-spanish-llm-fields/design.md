## Context

LLM output for a partida flows through the service untouched: `objetivo`, `inventario`, and `opciones` are passed straight from the validated LLM response into the persisted partida and on to the frontend (see `partida_service.py` creation/turn paths and `partidas.py` resume). No translation or post-processing exists today.

Language is asserted globally in the prompts and reinforced for prose (`narrativa`, `resumen_historia`), but the short label-like fields are under-specified and drift to English — primed by the explicitly-English `_en` fields that share the same JSON object. `objetivo` is generated once at creation and never regenerated, so an English slip persists for the life of the game; `opciones` regenerate each turn, so they drift intermittently.

This change is two pieces with very different shapes: a forward fix (prompts + schema) that prevents new drift, and a backward fix (one-off remediation) for partidas already poisoned.

## Goals / Non-Goals

**Goals:**
- Stop new partidas from emitting `objetivo`/`inventario`/`opciones` in English.
- Pin the language rule once, anchored to the existing `_en` convention, so it is robust and self-documenting.
- Correct legacy partidas already persisted with English fields, safely and idempotently.

**Non-Goals:**
- No language detection/validation-and-retry in the hot path. The problem is prompt under-specification, not model incapacity; adding `langdetect` + retry would add latency and a dependency to every turn. Out of scope.
- No change to persisted schema shape, API contracts, or frontend.
- No re-translation of `narrativa`/`resumen_historia` history; those already render in Spanish and are large. Only the short, currently-leaky fields are in scope for remediation.

## Decisions

### Decision: One bidirectional rule anchored to `_en`, not per-field prose

Add a single hard rule to both system prompts: *all text fields are Spanish rioplatense except fields whose name ends in `_en`, which are English.* The model already honors `_en` perfectly for the English direction; making the convention an explicit two-way contract is the highest-leverage lever and stays correct if new fields are added later.

**Alternative considered — enumerate each Spanish field in prose:** brittle, drifts out of sync as the schema evolves, and repeats what the schema already names.

### Decision: Reinforce with JSON-schema `description` on the leaky fields only

Add `description: "En español rioplatense (es-AR)"` (or equivalent) to `objetivo`, `inventario_inicial`, `agregar_inventario`/`quitar_inventario` items, and `opciones` in both schemas. Schema descriptions are read by the model precisely when it emits a field's value, so this puts the instruction where short fields drift. Limit to the leaky fields to avoid noise; `_en` fields and long prose don't need it.

**Alternative considered — rename fields to `_es` suffix:** mirrors `_en` symmetrically but is a breaking change to the domain models, repo, and frontend types for no added enforcement the `description` doesn't already give.

### Decision: Remediate legacy partidas with a one-off LLM translate-if-needed pass

A standalone script (run once, manually, not on the request path) enumerates partidas from the Cosmos `partidas` container and, per partida, sends the short fields through the existing Foundry chat client with a translate-if-needed instruction: *return the text in Spanish rioplatense; if it is already Spanish, return it verbatim.* This collapses detection + translation + idempotency into one call and reuses infrastructure already configured.

**Alternative considered — regenerate `objetivo` from the LLM fresh:** would invent a new objective inconsistent with a game already in progress. Translation preserves meaning; regeneration breaks coherence.

**Alternative considered — `langdetect` gate before translating:** short strings ("torch") detect unreliably; the LLM translate-if-needed instruction is more robust for 1–5 word values and removes the dependency.

### Decision: Scope remediation to `objetivo` and inventory; leave `opciones`

`objetivo` is the high-value target (sticky, always visible). Current inventory entries are worth correcting too. `opciones` are ephemeral — only the latest turn's options are actionable and the next turn regenerates them under the fixed prompt — so remediating historical options is not worth the cost. The script corrects `world_state.objetivo` and `personaje.inventario`; it may optionally normalize the latest turn's `opciones` if cheap, but historical turns are left as-is.

## Risks / Trade-offs

- **Translation alters a correct Spanish objetivo** → the translate-if-needed prompt instructs verbatim return for already-Spanish input; run against a dry-run/log mode first and spot-check before persisting.
- **Cost/time over a large partidas container** → one cheap chat call per partida on `gpt-4.1-mini`; batchable and re-runnable. Idempotency makes partial runs safe to resume.
- **Mid-flight partidas during deploy** → forward fix is prompt-only and takes effect on the next turn; no coordination with the migration needed. Migration can run any time after deploy.
- **No automated language test in CI** → mitigated by the schema `description` + prompt rule being assertable in unit tests (string presence), and the spec scenarios documenting expected behavior. Full output-language verification stays manual.

## Migration Plan

1. Ship the forward fix (prompts + schema + `PROMPT_VERSION` bump). New partidas are correct from here on.
2. Run the remediation script in dry-run/log mode over the `partidas` container; review a sample of proposed translations.
3. Run it in write mode. It is idempotent, so it can be re-run or resumed safely.
4. Rollback: the forward fix is a prompt/schema revert if needed; the migration has no schema change to roll back, and translated values are persisted partida documents (restore from Cosmos backup only if a translation regresses meaning, which dry-run review is designed to catch).

## Open Questions

- Should the migration also normalize the latest turn's `opciones`, or is leaving all options to natural regeneration acceptable? (Leaning: leave them.)
- Exact `description` wording / locale tag to use (`es-AR` vs "español rioplatense") for consistency with existing prompt language.
