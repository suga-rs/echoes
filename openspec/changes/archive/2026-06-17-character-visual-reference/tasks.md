## 1. Domain model

- [x] 1.1 Add `referencia_visual_url: str | None = None` to `Personaje` in `app/models/domain.py`
- [x] 1.2 Confirm Cosmos deserialization of existing partidas defaults the new field to `None` (schemaless safe)

> Note: also added `MetadataPartida.usa_referencia_visual: bool = False` as the new-games gate (see design.md decision #2 — `None` alone can't distinguish a new game from an old one).

## 2. Foundry client — image edit

- [x] 2.1 Write a failing test for a new `FoundryClient.editar_imagen(prompt, reference_bytes, *, size, input_fidelity)` (mock `images.edit`)
- [x] 2.2 Implement `editar_imagen` wrapping `self._client.images.edit(...)` with `input_fidelity`, reusing `_with_retries` and telemetry (mirror `generar_imagen`: jpeg, b64 decode, FoundryError handling)
- [x] 2.3 Verify the test passes; add a test for the empty/URL-only response error paths

## 3. Reference prompt builder

- [x] 3.1 Write a failing test for a new `prompts.build_reference_prompt(descripcion_visual_en, genero)` asserting it includes the visual description, the genre style, "full-body / neutral background / single subject / no text", and NO scene text
- [x] 3.2 Implement `build_reference_prompt`; verify test passes

## 4. Service — lazy reference + edit-based scenes

- [x] 4.1 Write a failing test: first image call on a game with no reference generates a reference (via `generar_imagen`), stores the URL on `personaje`, does NOT increment `imagenes_generadas`, then produces the scene via `editar_imagen`
- [x] 4.2 Write a failing test: second image call reuses the stored reference (no new reference generation) and increments the counter for the scene
- [x] 4.3 Write a failing test: reference generation failure falls back to text-only `generar_imagen` for that scene and leaves `referencia_visual_url` as `None` (retried next call)
- [x] 4.4 Write a failing test: when a game is at `MAX_IMAGENES_POR_PARTIDA`, neither reference nor scene image is generated
- [x] 4.5 Implement the lazy "ensure reference exists" step inside `_generar_imagen_segura`: fetch reference bytes from blob, call `editar_imagen` for the scene; keep cap check before any generation
- [x] 4.6 Verify all four image paths (creation auto, turn auto, on-demand `generar_imagen_turno`, streaming final) persist the partida after a first-image call so the reference URL is saved
- [x] 4.7 Run `pytest` for the service module; verify green

## 5. Frontend — game-start loading state

- [x] 5.1 Add a loading state in the game-start flow (`page.tsx` / inicio-dialog) shown while the first turn + image are produced
- [x] 5.2 Ensure the loading state clears once the first turn (with image) arrives, and on error resets cleanly
- [x] 5.3 Run `pnpm typecheck` and `pnpm lint`

## 6. Verification

- [x] 6.1 Run full backend `pytest` and `ruff check .`
- [ ] 6.2 Manually start a new game against the live deployment; confirm a reference is generated once, scenes use `images.edit`, and the protagonist stays visually consistent across turns
- [ ] 6.3 Confirm an existing (pre-change) game still renders images via the text-only path

> 6.2 and 6.3 are manual checks against the live Azure deployment (require credentials + visual inspection); left for the user to run.
