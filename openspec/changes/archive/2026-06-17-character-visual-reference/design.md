## Context

Image generation is funnelled through a single backend method, `PartidaService._generar_imagen_segura`, which every path calls: creation auto-image, turn auto-image, on-demand (`generar_imagen_turno`), and the streaming final image. It builds a prompt with `prompts.build_image_prompt` (`Character: {visual_en}. Scene: {scene_en}. Style: {genero}.`) and calls `FoundryClient.generar_imagen` → `images.generate`. Identity is carried only by the text `visual_en`, so the protagonist's face/body/outfit drift across turns.

The gpt-image-2 deployment (api_version `2025-04-01-preview`) is confirmed to support `images.edit` with `input_fidelity`, which preserves a subject's identity from a reference image. The single chokepoint and the existing `Character:`/`Scene:` split in the prompt are the seams this design slots into.

## Goals / Non-Goals

**Goals:**
- Keep one protagonist visually consistent across all images in a game.
- Generate the canonical reference exactly once per game, lazily, reusing the existing image chokepoint so no path is special-cased.
- Keep the reference generation free of the `MAX_IMAGENES_POR_PARTIDA` budget.
- Cover the longer first-image step with a game-start loading state.

**Non-Goals:**
- Migrating existing games (they keep the text-only path).
- Multi-view character sheets (single full-body portrait is v1; sheets are a possible future lever).
- Consistency of NPCs or locations across turns.
- Any new seed/determinism mechanism beyond reference + `input_fidelity`.

## Decisions

### 1. Reference artifact: single full-body portrait, neutral background
A clean full-body portrait on a neutral background, rendered in `ESTILO_POR_GENERO[genero]`, captures face + outfit + body with zero scene clutter to leak into later edits.
- **Why not a multi-view sheet?** A sheet is richer but ambiguous input to `edit()` ("compose using which pose?") and harder to render cleanly. With `input_fidelity="high"`, one good clean reference is sufficient. Sheet stays a v2 fallback if re-posing looks stiff.
- The reference prompt = `descripcion_visual_en` + style + "full-body, single subject, neutral background, no text" — **no scene**.

### 2. New-games gate via a creation flag; lazy, memoized generation inside the chokepoint
`MetadataPartida` gains `usa_referencia_visual: bool = False`, set `True` only by `crear_partida`. Old documents deserialize as `False` (schemaless-safe) and stay on the text-only path forever; new games opt in at creation.

`_generar_imagen_segura` gains a first step **gated on that flag**: if `usa_referencia_visual` is `True` and `personaje.referencia_visual_url` is `None`, generate the reference (`images.generate`), upload it, store the URL on the character; otherwise reuse the stored reference. Then the scene image is produced via `images.edit` against the reference. If the flag is `False`, the method behaves exactly as today (`images.generate` from text).
- **Why a flag and not just the `None` check?** A brand-new game *also* starts with `referencia_visual_url is None`, so `None` alone can't tell "new game, generate a reference" from "old game, never use one." An old game requesting an on-demand image after deploy would wrongly trigger reference creation. The creation flag is the honest discriminator and satisfies the "new games only" requirement.
- **Why lazy not eager-at-creation?** Creation already triggers the first scene image, so the reference is generated at game start in practice anyway — but routing through the chokepoint means no special-casing, and a game that renders zero images never pays for a reference. One code path covers all four entry points.
- `referencia_visual_url is None` is the per-game memoization trigger *within* the flagged path: generated once, reused thereafter.

### 3. Reference is not counted against the image cap
The reference generation does not touch `metadata.imagenes_generadas`. Only the scene `edit()` increments it. The cap check (`imagenes_previas >= max`) still gates scene images; if a game is at its cap, no reference is generated either (no image will be produced anyway).

### 4. Scene images use `images.edit` + `input_fidelity="high"`
New `FoundryClient.editar_imagen(prompt, reference_bytes, size, input_fidelity)` wraps `images.edit`. `build_image_prompt` is reused as the edit prompt: identity comes from the reference pixels, while the `Character:` text reinforces outfit/colors against re-pose drift and `Scene:` drives composition.
- Reference bytes are fetched from blob storage (URL stored on `Personaje`) for each edit call.

### 5. Frontend loading state at game start
Game start now does two image calls back to back (reference, then first scene edit). The start flow shows an explicit loading state until the first turn (with image) is ready, instead of appearing frozen.

## Risks / Trade-offs

- **`images.edit` semantics differ from `generate`** (multipart upload of reference bytes, different params) → isolate in `editar_imagen` with its own retry/telemetry path mirroring `generar_imagen`; fail soft like today (image failures already return `None` and don't break the turn).
- **Reference "paste" flattening scenes** — model may reuse the reference's pose/lighting → keep `Scene:` text authoritative for composition; multi-view sheet is the escalation if needed.
- **Longer, costlier game start** (2 generations) → loading state covers UX; reference is uncounted so it's one-time, not per-turn.
- **Reference generation fails** → fall back to the text-only `generate()` path for that image so the game still renders something; retry reference creation on the next image call (still `None`).
- **Persisting the reference URL** — the URL is set on `personaje` in-memory inside the chokepoint; each caller already persists the `partida` afterward, so verify all four paths persist after a first-image call so the URL isn't lost.

## Migration Plan

No data migration. New games populate `referencia_visual_url` on first image; existing games leave it `None` and continue on the text-only `generate()` path. Rollback is removing the lazy step and reverting scene calls to `generar_imagen` — stored reference URLs become inert, no cleanup needed.

## Open Questions

- None blocking. Multi-view sheet vs single portrait is settled for v1 (portrait); revisit only if re-posing quality is poor.
