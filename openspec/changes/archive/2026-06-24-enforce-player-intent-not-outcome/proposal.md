## Why

The player's free-text action is injected verbatim into the phase-1 turn prompt, and nothing tells the narrator that this text is the player's *intent*, never the *outcome*. When a player phrases an uncertain action as a done deal — "Realizo un último ataque al corazón del guardia **y lo mato**" — the narrator obeys: it sets `requiere_tirada = null` and narrates the kill, skipping the d20 entirely. The dice system is sound, but its only gate (the phase-1 decision of *whether* to roll) is fully steerable by player wording, which lets players author the resolution of actions they should never resolve.

## What Changes

- Add a hard rule to `SYSTEM_PROMPT_TURNO` distinguishing player **intention/decision** (legitimate: choosing to attack, persuade, climb) from player-authored **resolution/outcome** (illegitimate: "and I kill him", "and I succeed", "and he believes me"). The narrator strips any declared outcome and resolves only the attempt.
- An attempt whose result is not guaranteed REQUIRES a check, regardless of how the player phrased it. Player wording can never downgrade an uncertain action to `requiere_tirada = null`.
- An attempt that is impossible given the situation is narrated as a failed attempt **without** a roll (the player's declared success does not make it real), consistent with the existing trivial/impossible carve-out.
- Re-frame the action injection in `build_turno_user_prompt` so the player's text is clearly labelled as intent only, not narrative authority.
- Bump `PROMPT_VERSION`.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `skill-checks`: Add a requirement that the narrator treats the player's action text as intent only and never lets player-authored outcomes bypass the check declaration; reinforce that uncertain-but-possible actions always require a roll and impossible actions are narrated as failed attempts without a roll.

## Impact

- `backend/app/services/prompts.py`: new hard rule in `SYSTEM_PROMPT_TURNO`, re-framed action header in `build_turno_user_prompt`, `PROMPT_VERSION` bump.
- `backend/docs/prompts.md`: changelog entry for the prompt version bump (documentary source of truth).
- No code-path, schema, API, or data-model changes — both the synchronous and streaming turn flows already route through `SYSTEM_PROMPT_TURNO` + `build_turno_user_prompt`, so the prompt change covers both.
- Behavior change only: the LLM is steered to declare checks it previously skipped; no breaking changes.
