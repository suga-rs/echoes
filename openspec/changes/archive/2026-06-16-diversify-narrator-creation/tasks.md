## 1. Creative seeds (pools + sampler)

- [x] 1.1 Write failing tests for `sample_seed`: deterministic output with `random.Random(seed)`, valid for each `Genero`, returns one value per dimension
- [x] 1.2 Add `SemillaCreativa` dataclass and `CREATION_POOLS` (genre-keyed `nombres`/`premisas`/`tonos`/`aperturas`) in `app/services/prompts.py`
- [x] 1.3 Implement `sample_seed(genero, rng=None)` to pass the tests

## 2. Source-aware creation prompt

- [x] 2.1 Write failing tests for `build_creacion_user_prompt`: seed fields appear under an "inspiración" framing; player `premisa`/`tono` appear under a "honralo" framing; name-precedence note present
- [x] 2.2 Extend `build_creacion_user_prompt(genero, descripcion, seed, premisa=None, tono=None)` with the two-bucket rendering (player→honor, seed→inspire; `apertura` always seed; suggested name as fallback)
- [x] 2.3 Bump `PROMPT_VERSION` (and note the change in `docs/prompts.md` changelog)

## 3. Request/DTO model changes

- [x] 3.1 Write failing tests: `StartPartidaRequest` accepts optional `premisa`/`tono`, rejects overlong values (422), still requires `descripcion_personaje`
- [x] 3.2 Add optional length-capped `premisa`/`tono` to `StartPartidaRequest` in `app/models/domain.py`
- [x] 3.3 Write failing test: `PartidaResumen` exposes `prompt_version`, normalizing null → `"1.0.0"`
- [x] 3.4 Add `prompt_version` to `PartidaResumen` with null→`1.0.0` normalization

## 4. Service + repository wiring

- [x] 4.1 Write/extend failing tests for `crear_partida`: samples a seed and threads `premisa`/`tono` into the builder; existing creation tests still pass
- [x] 4.2 Update `crear_partida` to accept optional `premisa`/`tono`, call `sample_seed(genero)`, and pass all into `build_creacion_user_prompt`
- [x] 4.3 Update `app/api/partidas.py` to forward `body.premisa`/`body.tono` to the service
- [x] 4.4 Write failing test for `list_all`: returned resúmenes carry `prompt_version` (incl. legacy null → `1.0.0`)
- [x] 4.5 Update `partida_repo.list_all` query to select `c.metadata.prompt_version`

## 5. Frontend

- [x] 5.1 Regenerate/extend types: start payload gains optional `premisa`/`tono`; `PartidaResumen` gains `prompt_version` (`pnpm gen:types` or `lib/types.ts`)
- [x] 5.2 Update `lib/api.ts` start call to send `premisa`/`tono`
- [x] 5.3 Add collapsible "Opciones avanzadas" (premise + tono inputs) to `components/inicio-dialog.tsx`, collapsed by default
- [x] 5.4 Display `prompt_version` per partida in `components/partidas-list.tsx`

## 6. Verification

- [x] 6.1 Backend: `ruff check . && ruff format . && pytest` all green
- [x] 6.2 Frontend: `pnpm lint && pnpm typecheck && pnpm build` all green
- [ ] 6.3 Manual smoke: create games with/without player premise+tone and confirm name/premise/tone variety across runs; confirm partidas list shows versions (legacy → 1.0.0)
