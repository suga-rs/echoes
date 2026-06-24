## 1. Schema y modelos de datos

- [x] 1.1 Agregar `descripcion_visual_en` (string, en inglés) a `npc_encontrado` en `TURNO_JSON_SCHEMA` (`backend/app/models/llm_schema.py`), incluyéndolo en `required` y `properties`.
- [x] 1.2 Agregar `npcs_en_escena` (array de strings) a `generar_imagen` en `TURNO_JSON_SCHEMA`, con su descripción de contrato.
- [x] 1.3 Reflejar ambos campos en los modelos Pydantic `NPCEncontrado` y `GenerarImagen` (`npcs_en_escena` con default lista vacía).
- [x] 1.4 Agregar `descripcion_visual_en: str | None = None` al modelo de dominio `NPC` (`backend/app/models/domain.py`), retrocompatible con partidas previas.

## 2. Prompts (contrato LLM)

- [x] 2.1 Actualizar `SYSTEM_PROMPT_TURNO` y `SYSTEM_PROMPT_RESOLUCION`: al introducir un NPC, emitir `descripcion_visual_en` (en inglés, detallado: edad, etnia, pelo, ojos, cuerpo, vestimenta, accesorios), y declarar en `generar_imagen.npcs_en_escena` los NPCs conocidos presentes en la escena (por nombre).
- [x] 2.2 Definir constante de tope de NPCs anclados por imagen (ej. `MAX_NPCS_ANCLADOS = 2`) en `prompts.py`.
- [x] 2.3 Modificar `build_image_prompt` para aceptar una lista de descripciones visuales de NPC ya resueltas e inyectar una sección `Also present: ...` entre `Character:` y `Scene:`.
- [x] 2.4 Bumpear `PROMPT_VERSION` y actualizar el changelog en `docs/prompts.md`.

## 3. Servicio: persistencia y resolución

- [x] 3.1 En `_aplicar_actualizaciones` (`partida_service.py`), persistir `descripcion_visual_en` del NPC al registrarlo por primera vez.
- [x] 3.2 Implementar helper de resolución tolerante: dado `npcs_en_escena` y `world_state.npcs`, devolver las descripciones visuales canónicas (case-insensitive + trim, ignorando nombres no resueltos o sin descripción), aplicando el tope `MAX_NPCS_ANCLADOS`.
- [x] 3.3 Cablear la resolución en el path síncrono: calcular los descriptores desde el turno + `world_state` y pasarlos a `_generar_imagen_segura` / `build_image_prompt` (cubre `crear_partida`, `avanzar_turno`, `generar_imagen_turno`).
- [x] 3.4 Cablear la resolución en el path de streaming (`_avanzar_turno_stream_impl`), reusando el mismo helper.

## 4. Tests

- [x] 4.1 Tests de schema/modelos: `npc_encontrado` con `descripcion_visual_en` y `generar_imagen` con `npcs_en_escena` validan y deserializan; `npcs_en_escena` ausente → lista vacía; `NPC` previo sin `descripcion_visual_en` deserializa como None.
- [x] 4.2 Tests de `build_image_prompt`: incluye los descriptores de NPC cuando se pasan; sin NPCs el prompt es equivalente al actual.
- [x] 4.3 Tests del helper de resolución: match tolerante (case/whitespace), nombre alucinado ignorado, NPC sin descripción ignorado, tope respetado.
- [x] 4.4 Tests de servicio: al introducir un NPC se persiste su `descripcion_visual_en`; en un turno con `npcs_en_escena`, el prompt de imagen generado incluye la descripción canónica del NPC presente (síncrono y streaming).

## 5. Verificación

- [x] 5.1 `ruff check .` y `ruff format .` sin errores en `backend/`.
- [x] 5.2 `pytest` en `backend/` en verde.
