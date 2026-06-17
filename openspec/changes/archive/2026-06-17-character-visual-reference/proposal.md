## Why

Character appearance drifts across a game's images. Today the only thread tying turn 1's character to turn 12's is a paragraph of English text (`Personaje.descripcion_visual_en`) re-rendered from scratch on every `images.generate` call. Text-to-image is many-to-one in reverse: the same description maps to a different face, body, and outfit colors each time, so the protagonist looks like a different person scene to scene. Our gpt-image-2 deployment exposes `images.edit` with `input_fidelity`, which lets a fixed reference image anchor identity by pixels — a far stronger lever than re-describing in words.

## What Changes

- Generate a **canonical character reference image** once per game (full-body portrait, neutral background, rendered in the genre style) from the existing `descripcion_visual_en`.
- Persist the reference image URL on the character so it survives reloads.
- Switch per-scene image generation from `images.generate` (text only) to `images.edit` with the stored reference image and `input_fidelity="high"`, so every scene is anchored to the same visual identity.
- Generate the reference **lazily and exactly once**, inside the existing single image chokepoint, on the first image any game needs; reuse it for all subsequent images.
- The reference generation is **not counted** against `MAX_IMAGENES_POR_PARTIDA`.
- **New games only** — existing games keep the text-only path; no migration.
- Surface a **loading state at game start** to cover the now-longer first-image step (reference generation followed by the first scene edit — two image calls back to back).

## Capabilities

### New Capabilities
- `character-visual-reference`: A per-game canonical character reference image, lazily generated once and reused to anchor identity across all scene images via the image-edit endpoint.

### Modified Capabilities
<!-- No existing spec governs image generation; nothing's requirements change. -->

## Impact

- **Backend**
  - `app/models/domain.py`: `Personaje` gains `referencia_visual_url: str | None = None`.
  - `app/services/foundry_client.py`: new `editar_imagen(...)` wrapping `images.edit` with `input_fidelity`; existing `generar_imagen` reused for the reference.
  - `app/services/partida_service.py`: `_generar_imagen_segura` gains the lazy "ensure reference exists" step; all four image paths (creation auto, turn auto, on-demand, streaming final) inherit it.
  - `app/services/prompts.py`: new reference-portrait prompt builder; `build_image_prompt` becomes the edit prompt (character text reinforces the reference).
- **Frontend**
  - Game-start flow shows a loading state while the first image (reference + scene) is produced.
- **External**: extra one-time `images.edit`-compatible reference generation per game; Azure Foundry gpt-image-2 deployment (already confirmed to support `images.edit` + `input_fidelity`).
- **Cost**: +1 uncounted image generation per game; per-scene cost roughly unchanged (edit vs generate).
