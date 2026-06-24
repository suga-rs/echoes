## Context

El protagonista se mantiene consistente entre imágenes gracias a `character-visual-reference`: una imagen de referencia canónica generada una vez y re-inyectada en cada escena vía `images.edit` con `input_fidelity="high"`. Los NPCs no tienen equivalente. Hoy el modelo `NPC` (`backend/app/models/domain.py`) guarda solo `nombre`, `descripcion` (en español, para narrativa) y `actitud`. El prompt de imagen (`build_image_prompt` en `backend/app/services/prompts.py`) solo incluye la descripción visual del protagonista y la descripción de la escena; además, el sistema instruye al narrador a NO describir personajes en `descripcion_escena_en`. Por eso cualquier NPC que aparece en una imagen sale de texto ad-hoc distinto en cada turno → deriva visual.

La restricción dura del cambio: no aumentar costo ni tiempo de generación de imágenes. Eso descarta (en este cambio) generar referencias de imagen por NPC o pasar múltiples imágenes a `images.edit`.

## Goals / Non-Goals

**Goals:**
- Persistir una descripción visual canónica por NPC, emitida por el LLM al introducirlo.
- Permitir al LLM declarar qué NPCs conocidos están presentes en la escena de cada turno.
- Inyectar las descripciones canónicas de los NPCs presentes en el prompt de imagen, junto a la del protagonista.
- Costo de imagen sin cambios: un solo `images.edit` por escena, igual que hoy; el delta es texto en el prompt.
- Retrocompatibilidad total con partidas y NPCs previos (campos nullable, degradación suave).

**Non-Goals:**
- No se generan imágenes de referencia por NPC (eso sería la futura Opción B/C).
- No se pasa más de una imagen a `images.edit`.
- No se cambia el flujo de referencia del protagonista (`character-visual-reference` queda intacto).
- No se toca el frontend: el anclaje es 100% server-side.
- No se migran partidas previas.

## Decisions

### Decisión 1: Descripción visual canónica de NPC capturada en la introducción

Se agrega `descripcion_visual_en` al objeto `npc_encontrado` del schema del turno (`llm_schema.py`), reflejado en el modelo Pydantic `NPCEncontrado` y persistido en el modelo de dominio `NPC` como campo nullable. Se captura **solo** cuando el NPC se registra por primera vez (la lógica existente en `_aplicar_actualizaciones` ya ignora `npc_encontrado` si el nombre ya existe), por lo que la descripción queda fija de por vida del NPC.

- **Por qué en la introducción y no por turno:** un descriptor por turno reintroduce exactamente la deriva que queremos eliminar. La estabilidad viene de capturarlo una vez y reusarlo.
- **Alternativa descartada:** derivar el visual del NPC desde su `descripcion` narrativa en español traduciéndola en el backend → costaría una llamada LLM extra y produciría texto menos controlado que pedírselo al narrador directamente en inglés.

### Decisión 2: Presencia declarada en el bloque `generar_imagen`

Se agrega `npcs_en_escena` (array de strings, nombres) a `generar_imagen` en el schema y en el modelo `GenerarImagen`. El narrador ya recibe la lista canónica de NPCs en el user-prompt del turno (`_format_npcs`), así que listar cuáles están presentes es coherencia narrativa que ya maneja.

- **Por qué nombres y no índices/IDs:** los NPCs se identifican por `nombre` en todo el dominio; no hay IDs estables. Reusar el nombre evita introducir un identificador nuevo.
- **Por qué en `generar_imagen` y no en `actualizaciones_estado`:** la presencia es información puramente visual para componer la imagen, vive junto a `descripcion_escena_en` y `necesaria`.

### Decisión 3: Resolución por nombre tolerante + degradación suave

El backend resuelve cada nombre de `npcs_en_escena` contra `world_state.npcs` con matching normalizado (case-insensitive, trim). Si no resuelve, o el NPC no tiene `descripcion_visual_en`, se ignora ese nombre. La imagen se genera siempre.

- **Por qué tolerante:** el LLM puede abreviar o variar el nombre; un match estricto perdería anclajes legítimos.
- **Por qué degradación suave:** consistente con el resto del sistema (la referencia del protagonista también degrada a texto si falla). Un nombre alucinado no debe romper el turno.

### Decisión 4: `build_image_prompt` acepta los descriptores de NPC

`build_image_prompt` gana un parámetro nuevo (lista de descriptores visuales de NPC, ya resueltos por el servicio). El servicio hace la resolución nombre→NPC→`descripcion_visual_en` y pasa la lista. El prompt agrega una sección tipo `Also present: <visual 1>; <visual 2>.` entre `Character:` y `Scene:`.

- **Tope de anclaje:** se limita a los primeros N (ej. 2) NPCs con descripción para no inflar el prompt ni confundir rasgos en el modelo de imagen. N como constante del módulo de prompts.
- **Ambos paths:** la inyección se aplica en el path síncrono (`_generar_imagen_segura` → llamado desde `crear_partida`, `avanzar_turno`, `generar_imagen_turno`) y en el de streaming. Como `_generar_imagen_segura` es el único punto de armado del prompt de imagen, basta con que reciba los descriptores de NPC resueltos; el servicio los calcula a partir del turno y del `world_state`.

### Decisión 5: Bump de `PROMPT_VERSION` y doc

Cambia el contrato JSON (nuevos campos) y las instrucciones de sistema (creación y turno). Se bumpea `PROMPT_VERSION` y se actualiza `docs/prompts.md` con el changelog, según la convención del repo.

## Risks / Trade-offs

- **Anclaje por texto no fija la cara como una imagen de referencia** → Mitigación: aceptado por diseño; este cambio reduce la deriva (edad, ropa, rasgos generales consistentes) a costo casi nulo. La fijación fuerte de identidad de un NPC queda para una futura Opción B/C (referencia de imagen para el antagonista recurrente), que este diseño habilita reusando `npcs_en_escena`.
- **El narrador no emite `descripcion_visual_en` al introducir un NPC** → Mitigación: campo nullable + degradación suave; sin descripción, ese NPC simplemente no se ancla (comportamiento actual). Las instrucciones de sistema lo piden explícitamente para maximizar cobertura.
- **Prompt de imagen demasiado largo si hay muchos NPCs** → Mitigación: tope de N NPCs anclados por imagen.
- **El narrador lista NPCs no presentes o alucinados** → Mitigación: resolución tolerante que ignora lo que no matchea; la lista es referencia, no fuente de verdad.
- **Retrocompat:** partidas y NPCs previos sin el campo → nullable y tratados como "sin ancla"; sin migración.
