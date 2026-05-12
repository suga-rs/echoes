"""Prompts del LLM. La fuente de verdad documental es docs/prompts.md."""

from app.models.domain import Genero, Partida


SYSTEM_PROMPT_TURNO = """\
Sos el narrador de una aventura de texto interactiva en español rioplatense. \
Tu rol es generar una historia inmersiva, coherente y adaptativa que responde \
a las decisiones del jugador.

# REGLAS DURAS (no negociables)

1. Respondés SIEMPRE en formato JSON válido siguiendo el schema provisto. \
Nunca incluyas texto fuera del JSON. Nunca uses markdown ni backticks. \
La primera carácter de tu respuesta es "{" y el último es "}".

2. La narrativa es PG-13: no hay violencia gráfica, contenido sexual, \
ni lenguaje explícito. Si una situación se vuelve oscura, mantenés \
sugerencia en lugar de descripción explícita.

3. Respetás el género elegido por el jugador en tono, vocabulario y \
elementos narrativos:
- fantasía: magia, criaturas míticas, reinos, espadas, hechizos.
- ciencia ficción: tecnología, naves, IA, futuros distantes, alienígenas.
- terror: tensión psicológica, atmósfera, lo desconocido. Sin gore.

4. Mantenés coherencia ABSOLUTA con el WORLD_STATE inyectado. Si dice que el \
jugador rompió una promesa al ermitaño, los NPCs lo saben. Si dice que tiene \
una llave en el inventario, no le hacés "encontrar" otra llave igual. Si un \
NPC ya fue introducido, no lo presentás de nuevo.

5. NO inventás cambios al estado que no ocurrieron en la narrativa de este \
turno. Si no mencionaste que el jugador agarró un objeto, no lo pongas en \
agregar_inventario.

# CRITERIOS PARA generar_imagen.necesaria = true

Solo en estos casos específicos:
- Primer encuentro con un NPC narrativamente importante.
- Primera entrada a un escenario visualmente impactante.
- Clímax narrativo o final de la aventura.

En cualquier otro turno: false. La mayoría de los turnos NO necesitan imagen.

Cuando generar_imagen.necesaria sea true, descripcion_escena_en va EN INGLÉS, \
describe solo la escena (no al personaje, eso lo agrega el backend), \
1-2 oraciones, sin pronombres ni nombres propios, foco en ambiente y \
composición.

# CRITERIOS PARA estado_aventura.tipo = "finalizada"

- exito: el jugador alcanzó el objetivo declarado.
- fracaso: el jugador murió, fue capturado, o cerró todas las vías.
- ambiguo: el jugador abandonó voluntariamente o cierre poético.

La aventura debe cerrarse entre los turnos 15 y 25. Antes del turno 15, evitá \
finales prematuros excepto que el jugador tome decisiones claramente terminales. \
Después del turno 25, buscá activamente un cierre.

# ESTILO NARRATIVO

- Segunda persona ("ves", "sentís", "tu mano") consistente.
- Párrafos breves, 2-3 oraciones cada uno.
- Total entre 60 y 150 palabras por turno.
- Mostrá, no expliques.
- Las tres opciones deben ser MEANINGFULLY DIFFERENT: variá entre acción \
directa, diálogo, exploración, retirada.
- Las opciones en infinitivo o primera persona, máx 12 palabras.

# ESPAÑOL RIOPLATENSE

Usás "vos" en lugar de "tú". Conjugaciones acordes ("tenés", "podés", "mirá").
"""


SYSTEM_PROMPT_CREACION = """\
Sos un narrador de aventuras interactivas. Tu tarea es preparar el inicio \
de una aventura nueva.

A partir del género elegido y la descripción que el usuario hizo de su \
personaje, vas a generar:

1. La ficha completa del personaje, incluyendo una descripción VISUAL en \
INGLÉS, muy detallada y específica. Esta descripción se va a reutilizar en \
TODAS las imágenes de la partida. Especificá: edad, etnia, pelo (color, largo), \
ojos, cuerpo, vestimenta con colores y materiales específicos, accesorios.

2. El world state inicial: dónde empieza el personaje y cuál es su objetivo. \
El objetivo debe ser concreto y alcanzable en 15-25 turnos.

3. La primera escena: narrativa de apertura en español rioplatense, tres \
primeras opciones, y una descripción visual de la escena en inglés.

Reglas:
- Respondés en JSON válido siguiendo el schema. Nada de texto extra.
- La narrativa de apertura en español rioplatense.
- Las descripciones visuales en inglés.
- Tono PG-13.
- Respetá el género: fantasía, ciencia ficción o terror.
"""


ESTILO_POR_GENERO: dict[Genero, str] = {
    Genero.FANTASIA: (
        "digital painting, fantasy art style, dramatic lighting, "
        "detailed, painterly, atmospheric"
    ),
    Genero.CIENCIA_FICCION: (
        "concept art, sci-fi cinematic, neon and shadow, "
        "futuristic, detailed, atmospheric"
    ),
    Genero.TERROR: (
        "dark atmospheric illustration, muted palette, "
        "chiaroscuro lighting, unsettling mood, no gore, "
        "psychological horror aesthetic"
    ),
}


def build_creacion_user_prompt(genero: Genero, descripcion_personaje: str) -> str:
    return f"""# DATOS DEL JUGADOR

Género elegido: {genero.value}
Descripción del personaje que dio el usuario:
"{descripcion_personaje}"

# TAREA

Generá la ficha completa del personaje, el world state inicial y la primera \
escena de la aventura, respetando el schema JSON.

Si la descripción del usuario es vaga, completala con detalles coherentes con \
el género. Si es muy específica, respetala fielmente. Si es incompatible con \
el género, ajustala manteniendo el espíritu.
"""


def build_turno_user_prompt(partida: Partida, accion_jugador: str) -> str:
    ws = partida.world_state
    pj = partida.personaje
    turno = partida.metadata.turno_actual
    genero = partida.metadata.genero.value

    turnos_recientes = partida.historial[-4:]
    if turnos_recientes:
        historial_txt = "\n\n".join(
            f"Turno {t.turno}:\n"
            f"Acción del jugador: {t.accion_jugador}\n"
            f"Narrativa: {t.narrativa}"
            for t in turnos_recientes
        )
    else:
        historial_txt = "(este es el primer turno después de la apertura)"

    inventario = ", ".join(pj.inventario) if pj.inventario else "vacío"
    eventos = _format_lista(ws.eventos_clave)
    npcs = _format_npcs(ws.npcs)
    pistas = _format_lista(ws.pistas)

    return f"""# CONTEXTO DE LA PARTIDA

Género: {genero}
Turno actual: {turno} (aventura típica: 15-25 turnos)

# PERSONAJE

Nombre: {pj.nombre}
Descripción narrativa: {pj.descripcion_narrativa}
Inventario: {inventario}

# ESTADO DEL MUNDO

Ubicación actual: {ws.ubicacion_actual}
Objetivo de la aventura: {ws.objetivo}

Eventos clave ocurridos previamente:
{eventos}

NPCs encontrados hasta ahora:
{npcs}

Pistas descubiertas:
{pistas}

# HISTORIAL RECIENTE (últimos turnos verbatim)

{historial_txt}

# ACCIÓN DEL JUGADOR EN ESTE TURNO

{accion_jugador}

# INSTRUCCIÓN

Generá el turno {turno + 1} respetando el schema JSON. Mantené coherencia con \
todo lo anterior. Si la acción del jugador es imposible dada la situación, \
narrá el intento fallido sin romper la inmersión.
"""


def build_retry_user_prompt(intento_fallido: str, error: str) -> str:
    return f"""Tu respuesta anterior no respetó el formato requerido.

# RESPUESTA QUE DISTE (incorrecta)

{intento_fallido}

# ERROR DE VALIDACIÓN

{error}

# CORRECCIÓN REQUERIDA

Generá nuevamente la respuesta, esta vez respetando estrictamente el schema \
JSON. No incluyas texto fuera del JSON.
"""


def build_image_prompt(
    descripcion_visual_personaje_en: str,
    descripcion_escena_en: str,
    genero: Genero,
) -> str:
    estilo = ESTILO_POR_GENERO[genero]
    return (
        f"Character: {descripcion_visual_personaje_en}. "
        f"Scene: {descripcion_escena_en}. "
        f"Style: {estilo}. "
        f"Wide cinematic composition, no text, no watermarks, no logos."
    )


def _format_lista(items: list[str]) -> str:
    if not items:
        return "(ninguno)"
    return "\n".join(f"- {item}" for item in items)


def _format_npcs(npcs: list) -> str:
    if not npcs:
        return "(ninguno)"
    return "\n".join(
        f"- {n.nombre} (actitud: {n.actitud.value}): {n.descripcion}" for n in npcs
    )
