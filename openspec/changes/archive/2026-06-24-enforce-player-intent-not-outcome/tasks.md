## 1. Prompt changes

- [x] 1.1 In `backend/app/services/prompts.py`, add a hard rule to `SYSTEM_PROMPT_TURNO` (near the "TIRADAS DE DADO" section) stating: the player's action text is their *intention/decision*, never the *resolution*; if it asserts an outcome ("y lo mato", "y lo logro", "y me cree"), the narrator disregards that part and resolves only the attempt.
- [x] 1.2 In the same rule, state that an uncertain-but-possible attempt ALWAYS requires a check regardless of the player's wording, and an impossible attempt is narrated as a failed attempt without a roll (the asserted success does not occur).
- [x] 1.3 Reword Rule #6 ("RESPETÁS las decisiones del jugador") so it explicitly scopes "decision" to the attempt and excludes player-authored outcomes, keeping it consistent with the new rule.
- [x] 1.4 In `build_turno_user_prompt`, re-frame the `# ACCIÓN DEL JUGADOR EN ESTE TURNO` header so the injected text is clearly labelled as the player's intent only (e.g. an "INTENTO del jugador — su intención, NO el desenlace" framing).
- [x] 1.5 Confirm the trivial-action guidance and the `Cruzo la habitación vacía → null` example remain intact so the no-check path is preserved.

## 2. Versioning & docs

- [x] 2.1 Bump `PROMPT_VERSION` in `prompts.py` (minor version bump). Done: 3.2.0 → 3.3.0.
- [x] 2.2 Add a changelog entry describing this change. Note: the documented source of truth lives at `docs/prompts.md` (repo root), not `backend/docs/`; entry added there.

## 3. Verification

- [x] 3.1 Run `ruff check .` and `ruff format .` in `backend/`; run `pytest` and confirm existing tests still pass. Done: ruff clean, 231 passed (after updating the version-pin test `test_prompt_version_fue_bumpeada` to 3.3.0).
- [x] 3.2 Manual check against a running backend: submit "Realizo un último ataque al corazón del guardia y lo mato" on an in-progress game and confirm the turn declares a check (a `tirada` event/d20) instead of narrating the kill. _(Accepted/waived by user; not run in this session.)_
- [x] 3.3 Manual check: submit an impossible-as-success action ("Agito la mano y el guardia explota") and confirm it is narrated as a failed attempt with no roll. _(Accepted/waived by user; not run in this session.)_
- [x] 3.4 Manual check: submit a plain-intent action ("Ataco al guardia") and confirm normal check-or-narrate behavior is unchanged. _(Accepted/waived by user; not run in this session.)_
