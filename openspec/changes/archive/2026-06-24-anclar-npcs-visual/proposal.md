## Why

El protagonista se mantiene visualmente consistente entre imágenes porque está anclado a una imagen de referencia canónica (capability `character-visual-reference`). Los NPCs y enemigos no tienen ningún ancla: solo existen como texto narrativo en español, y su apariencia se reinventa de cero en cada generación porque la única descripción visual que llega al prompt de imagen es la del protagonista. El resultado es que el mismo NPC cambia de cara, ropa y edad de una imagen a otra.

Esta es la solución de menor costo: anclar a los NPCs por **texto canónico** —una descripción visual fija por NPC, reutilizada en cada escena donde aparece— sin agregar generaciones de imagen ni tiempo de render por turno.

## What Changes

- El LLM, al **introducir** un NPC (`npc_encontrado`), emite también una descripción visual en inglés (`descripcion_visual_en`), análoga a la del protagonista. Se persiste una sola vez por NPC.
- El LLM declara en el bloque `generar_imagen` qué NPCs ya conocidos están **presentes en la escena** de este turno (`npcs_en_escena`), referenciando nombres existentes.
- El backend cruza esos nombres contra los NPCs persistidos y **inyecta sus descripciones visuales canónicas** en el prompt de imagen de la escena, junto a la del protagonista.
- Matching tolerante y degradación suave: un nombre que no matchea (alucinado o mal escrito) simplemente se ignora; la imagen se genera igual.
- Tope de NPCs anclados por imagen para no inflar el prompt ni confundir rasgos.
- Sin cambios en el mecanismo de generación de imagen (sigue siendo un solo `images.edit` con la referencia del protagonista). El costo extra es ~texto en el prompt.

## Capabilities

### New Capabilities
- `npc-visual-consistency`: Persistencia de una descripción visual canónica por NPC y su reutilización en las imágenes de escena donde el NPC está presente, para mantener la apariencia de NPCs/enemigos consistente entre imágenes sin generaciones adicionales.

### Modified Capabilities
<!-- Ninguna: character-visual-reference no cambia sus requisitos; el flujo de protagonista se conserva intacto. -->

## Impact

- `backend/app/models/llm_schema.py`: nuevo campo `descripcion_visual_en` en `npc_encontrado`; nuevo campo `npcs_en_escena` en `generar_imagen`; modelos Pydantic correspondientes (`NPCEncontrado`, `GenerarImagen`).
- `backend/app/models/domain.py`: campo `descripcion_visual_en` en el modelo `NPC` (nullable, retrocompatible con partidas previas).
- `backend/app/services/prompts.py`: instrucciones de sistema (creación + turno) para emitir las descripciones visuales y la lista de presencia; `build_image_prompt` acepta e inyecta los descriptores de NPC.
- `backend/app/services/partida_service.py`: persistir `descripcion_visual_en` al registrar NPC; resolver `npcs_en_escena` → NPCs canónicos y pasarlos a `build_image_prompt` en ambos paths (síncrono y streaming).
- `docs/prompts.md` y `PROMPT_VERSION` (bump por cambio de contrato).
- Tests: `backend/tests/test_prompts.py` y los de servicio de partidas.
- Sin impacto en el frontend (la apariencia es server-side); sin impacto en el costo/tiempo de generación de imágenes.
