## Context

A turn is resolved in two LLM phases. Phase 1 (`SYSTEM_PROMPT_TURNO`) decides whether the action is uncertain and, if so, declares a check (`requiere_tirada = {habilidad, banda}`); phase 2 (`SYSTEM_PROMPT_RESOLUCION`) narrates the outcome honoring a real server-side d20. The dice mechanics are sound and fully server-owned — `_resolver_tirada` in `partida_service.py` rolls the die and the resolution prompt is constrained to honor it.

The weak point is the single boolean gate in phase 1. The player's free-text action (≤200 chars, `acciones.tsx`) is injected verbatim into `build_turno_user_prompt` under a neutral `# ACCIÓN DEL JUGADOR` header. Nothing frames this text as *intent*; meanwhile Rule #6 ("RESPETÁS las decisiones del jugador") gives the model semantic license to obey a player who writes "...y lo mato". The model then sets `requiere_tirada = null` and narrates the player-authored outcome, bypassing the die. Both the sync and streaming flows share this prompt path, so a prompt-level fix covers both.

## Goals / Non-Goals

**Goals:**
- Make phase 1 robust to player action text that asserts its own resolution: the narrator resolves the *attempt*, never the player-declared *outcome*.
- Keep uncertain-but-possible actions on the dice path no matter how the player phrased success.
- Keep impossible actions on the existing single-narration "failed attempt" path (no roll).
- Preserve legitimate player agency: choosing *what* to attempt is still honored.

**Non-Goals:**
- No code-path, schema, DTO, or data-model changes. This is a prompt-engineering change.
- No programmatic detection/sanitization of "outcome language" in the action string (brittle, YAGNI).
- No changes to the creation phase or to the narrator-generated options (scope confirmed: per-turn action only).
- No change to dice mechanics, DCs, modifiers, or the phase-2 resolution prompt.

## Decisions

### Decision 1: Fix at the prompt layer, not with code-side input parsing

Add a hard rule to `SYSTEM_PROMPT_TURNO` that draws the line between **intención/decisión** (the player picks an action) and **resolución/desenlace** (the player dictates the result), and re-frame the action header in `build_turno_user_prompt` to label the player text as intent only.

- **Why over alternatives:** Heuristic detection of "outcome phrasing" in the action string is brittle across free-form Spanish and easy to evade; a pre-pass LLM call to normalize the action doubles latency and cost for every turn. The root cause is that the prompt never told the narrator the player's text is intent — so the targeted, lowest-cost fix is to tell it, exactly where the text enters.

### Decision 2: The new rule narrows Rule #6 explicitly

Rule #6 currently reads as an unqualified "respect the player's decisions," which is the very license being abused. The new rule explicitly carves resolution out of "decision": the player decides the *attempt*; the dice and narrator decide the *result*. The two rules must be mutually consistent so the model does not see a contradiction.

- **Why:** Leaving Rule #6 unqualified next to a new "don't obey declared outcomes" rule creates a conflict the model may resolve in the wrong direction.

### Decision 3: Impossible-as-success → failed attempt without a roll

When the player declares success on something impossible ("agito la mano y el guardia explota"), the narrator narrates the failed attempt in a single narration and declares no check — consistent with the existing trivial/impossible carve-out. The default heuristic "ante la duda, TIRÁS" is unchanged; only genuinely impossible actions skip the die.

- **Why over a heroica roll:** Routing the absurd through a real d20 hands the player a non-zero chance that the impossible succeeds, which is worse than the bug being fixed. Chosen per product decision.

### Decision 4: Bump `PROMPT_VERSION` and update the changelog

Any change to `SYSTEM_PROMPT_*` bumps `PROMPT_VERSION` (per the comment in `prompts.py`); it is logged per LLM call and persisted in each game's metadata for quality correlation. Update `backend/docs/prompts.md`, the documentary source of truth, with a changelog entry. This is a minor behavior-shaping change → bump the minor version.

## Risks / Trade-offs

- **Over-correction: the narrator declares checks for trivial actions to be "safe."** → The new rule is scoped to player-*asserted resolutions*; the existing "trivial = null, ante la duda TIRÁS" guidance and its example (`Cruzo la habitación vacía → null`) are retained so the trivial path stays intact.
- **Prompt drift / regressions in unrelated behavior from editing a large system prompt.** → Keep the edit additive and localized (one new section + a clause on Rule #6); rely on the existing prompt-version telemetry and incoherence feedback to catch regressions.
- **LLM still occasionally obeys a cleverly worded outcome (non-determinism).** → Inherent to a prompt-level mitigation; this is the right altitude for the fix. The dice/resolution machinery remains the authoritative backstop whenever a check *is* declared. Residual leakage is acceptable and observable via player feedback.
- **Verification is non-deterministic (LLM behavior).** → Validate with the manual representative-action checks listed in tasks (the canonical "y lo mato" prompt and the impossible variant) against a running backend rather than a strict unit assertion on model output.

## Migration Plan

Stateless prompt change. Deploy normally; new turns immediately use the updated prompt and the bumped `PROMPT_VERSION`. In-flight games are unaffected (no schema or stored-state change). Rollback = revert the `prompts.py` edit and the version bump.

## Open Questions

None — the two design forks (impossible-action handling, scope) were resolved before authoring: impossible-as-success is narrated as a failed attempt without a roll, and the rule applies to the per-turn action only.
