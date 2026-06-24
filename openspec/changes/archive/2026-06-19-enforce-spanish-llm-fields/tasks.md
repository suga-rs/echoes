## 1. Forward fix — prompts

- [x] 1.1 Add the bidirectional language rule to `SYSTEM_PROMPT_TURNO` in `backend/app/services/prompts.py`: all text fields are español rioplatense except `_en`-suffixed fields, which are English.
- [x] 1.2 Add the same explicit rule to `SYSTEM_PROMPT_CREACION`, replacing the under-specified "Las descripciones visuales en inglés" wording with the bidirectional `_en` rule so `objetivo` and `inventario_inicial` are covered.
- [x] 1.3 Bump `PROMPT_VERSION` and add a changelog entry in `docs/prompts.md` describing the language rule.

## 2. Forward fix — JSON schema descriptions

- [x] 2.1 Add `description` ("En español rioplatense") to `opciones` items and `actualizaciones_estado.agregar_inventario` / `quitar_inventario` items in `TURNO_JSON_SCHEMA` (`backend/app/models/llm_schema.py`).
- [x] 2.2 Add `description` to `world_state_inicial.objetivo`, `personaje.inventario_inicial` items, and `primera_escena.opciones` items in `CREACION_JSON_SCHEMA`.

## 3. Tests for the forward fix

- [x] 3.1 Add a unit test asserting both system prompts contain the bidirectional `_en` language rule.
- [x] 3.2 Add a unit test asserting the leaky schema properties carry a Spanish `description`.
- [x] 3.3 Add/update a test asserting `PROMPT_VERSION` was bumped and is persisted on a newly created partida.

## 4. Legacy remediation script

- [x] 4.1 Add a standalone one-off script (e.g. `backend/scripts/remediar_idioma.py`) that enumerates partidas from the Cosmos `partidas` container via the existing repo/client.
- [x] 4.2 Implement a translate-if-needed call against the Foundry chat client: return `objetivo` and each `inventario` entry in español rioplatense, returning already-Spanish text verbatim (idempotent).
- [x] 4.3 Persist only `world_state.objetivo` and `personaje.inventario`; leave `_en` fields, narrative history, and all other state untouched.
- [x] 4.4 Support a dry-run/log mode that reports proposed translations without writing, plus a write mode.
- [x] 4.5 Make the script resumable/re-runnable safely (idempotent per partida).

## 5. Tests for remediation

- [x] 5.1 Test that a partida with an English `objetivo` is rewritten to Spanish and persisted (mocked LLM).
- [x] 5.2 Test idempotency: a partida already in Spanish, or a second run, leaves the document unchanged.
- [x] 5.3 Test that `_en` fields, history, and non-language state are preserved after remediation.

## 6. Rollout

- [x] 6.1 Run `ruff check .` and `pytest` in `backend/`; confirm green.
- [x] 6.2 Deploy the forward fix; verify a freshly created partida returns Spanish `objetivo`/`inventario`/`opciones`. _(requiere entorno live — lo corre el usuario)_
- [x] 6.3 Run the remediation script in dry-run mode over the `partidas` container and spot-check a sample. _(requiere Cosmos real — lo corre el usuario)_
- [x] 6.4 Run the remediation script in write mode. _(requiere Cosmos real — lo corre el usuario)_
