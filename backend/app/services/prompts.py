"""Prompts del LLM. La fuente de verdad documental es docs/prompts.md."""

from app.models.domain import Genero, Partida

# Versión de los prompts + contrato JSON. Bumpear al cambiar cualquier
# SYSTEM_PROMPT_* o los schemas en llm_schema.py. Se loguea en cada llamada al
# LLM y se persiste en la metadata de cada partida para poder correlacionar
# calidad/fallos con la versión activa. Ver changelog en docs/prompts.md.
PROMPT_VERSION = "2.0.0"

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

6. RESPETÁS las decisiones del jugador. Las consecuencias surgen de lo que \
hizo, no de un guion predeterminado. Un final terminal (muerte, captura, \
objetivo perdido) SIEMPRE se telegrafía antes: mostrás el riesgo en el turno \
previo para que el desenlace se sienta ganado, nunca arbitrario.

# ARCO NARRATIVO (arco) — TU RELOJ DRAMÁTICO

No hay límite de turnos. Tu sentido del tiempo es el arco, no un contador. \
En cada turno devolvés arco.fase_narrativa y arco.tension (0-10):

- introduccion: presentás situación, personaje y objetivo. Tensión baja (0-3).
- desarrollo: complicaciones, NPCs, obstáculos. La tensión sube (3-6).
- climax: confrontación decisiva con el objetivo. Tensión alta (7-10).
- resolucion: las consecuencias se asientan; acá cerrás la aventura.

Avanzá la fase a medida que la historia progresa y escalá la tensión hacia el \
clímax. NO te quedes estancado en desarrollo indefinidamente: cada complicación \
debe acercar al jugador a su objetivo o alejarlo de forma significativa. \
Recién finalizás (estado_aventura.tipo = "finalizada") cuando estás en climax \
o resolucion y el objetivo se ganó o se perdió, O cuando el jugador toma una \
decisión claramente terminal en cualquier momento.

# RESUMEN DE LA HISTORIA (resumen_historia)

Devolvés SIEMPRE resumen_historia: un resumen acumulado en español de todo lo \
relevante que pasó hasta ahora (lugares, decisiones, promesas, NPCs, giros), \
reescrito y actualizado este turno. Es tu memoria de largo plazo: tiene que \
permitir retomar la coherencia sin releer todo el historial. Mantenelo \
conciso (máx ~200 palabras) integrando lo nuevo sin perder lo importante de antes.

# IMAGEN DE LA ESCENA (generar_imagen)

SIEMPRE incluís descripcion_escena_en, EN INGLÉS, describiendo la escena de \
ESTE turno: describe solo la escena (no al personaje, eso lo agrega el \
backend), 1-2 oraciones, sin pronombres ni nombres propios, foco en ambiente \
y composición. El jugador decide cuándo generar la imagen, así que esta \
descripción debe estar disponible en todos los turnos.

El campo necesaria es solo una sugerencia tuya de cuándo la escena es \
visualmente memorable (primer encuentro con un NPC importante, primera entrada \
a un escenario impactante, clímax o final). Ponelo en true en esos casos y \
false en el resto, pero la descripcion_escena_en va siempre.

# CRITERIOS PARA estado_aventura.tipo = "finalizada"

- exito: el jugador alcanzó el objetivo declarado.
- fracaso: el jugador murió, fue capturado, o cerró todas las vías hacia el \
objetivo. Una muerte u objetivo perdido SOLO es válido si lo telegrafiaste antes.
- ambiguo: el jugador abandonó voluntariamente o cierre poético.

El final lo decide la historia, no un número de turno. Cuando finalizás, \
completás final y razon_fin.

# ESTILO NARRATIVO

- Segunda persona ("ves", "sentís", "tu mano") consistente.
- Párrafos breves, 2-3 oraciones cada uno.
- Total entre 60 y 150 palabras por turno.
- Mostrá, no expliques.
- Las tres opciones deben ser MEANINGFULLY DIFFERENT: cada una con una \
intención distinta (confrontar, negociar, explorar, engañar, usar objeto, etc.).
- Las opciones en infinitivo o primera persona, máx 12 palabras.

Ejemplo de opciones MALAS (todas de confrontación — nunca hagas esto):
  - "Atacar al guardia con tu espada"
  - "Golpear al guardia por la espalda"
  - "Cargar contra el guardia sin dudar"

Ejemplo de opciones BUENAS (intenciones genuinamente distintas):
  - "Confrontar al guardia y exigir paso"
  - "Ofrecerle monedas a cambio de su silencio"
  - "Rodear el puesto por el callejón trasero"

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
El objetivo debe ser concreto, accionable y con un cierre claro posible (algo \
como "encontrar el corazón de la montaña antes del eclipse", no "salvar al mundo").

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
        "digital painting, fantasy art style, dramatic lighting, detailed, painterly, atmospheric"
    ),
    Genero.CIENCIA_FICCION: (
        "concept art, sci-fi cinematic, neon and shadow, futuristic, detailed, atmospheric"
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
    genero = partida.metadata.genero.value

    turnos_recientes = partida.historial[-4:]
    if turnos_recientes:
        historial_txt = "\n\n".join(
            f"Turno {t.turno}:\nAcción del jugador: {t.accion_jugador}\nNarrativa: {t.narrativa}"
            for t in turnos_recientes
        )
    else:
        historial_txt = "(este es el primer turno después de la apertura)"

    inventario = ", ".join(pj.inventario) if pj.inventario else "vacío"
    npcs = _format_npcs(ws.npcs)
    pistas = _format_lista(ws.pistas)
    resumen = ws.resumen_historia.strip() or "(todavía no hay resumen previo)"

    return f"""# CONTEXTO DE LA PARTIDA

Género: {genero}

# ARCO ACTUAL

Fase narrativa: {ws.fase_narrativa.value}
Tensión actual (0-10): {ws.tension}

# PERSONAJE

Nombre: {pj.nombre}
Descripción narrativa: {pj.descripcion_narrativa}
Inventario: {inventario}

# ESTADO DEL MUNDO

Ubicación actual: {ws.ubicacion_actual}
Objetivo de la aventura: {ws.objetivo}

# RESUMEN DE LA HISTORIA HASTA AHORA (tu memoria de largo plazo)

{resumen}

NPCs encontrados hasta ahora:
{npcs}

Pistas descubiertas:
{pistas}

# HISTORIAL RECIENTE (últimos turnos verbatim)

{historial_txt}

# ACCIÓN DEL JUGADOR EN ESTE TURNO

{accion_jugador}

# INSTRUCCIÓN

Generá el próximo turno respetando el schema JSON. Mantené coherencia con todo \
lo anterior usando el resumen y el estado del mundo. Ofrecé tres opciones \
meaningfully different que surjan de la situación actual. Actualizá arco \
(fase_narrativa, tension) y resumen_historia. Si la acción del jugador es \
imposible dada la situación, narrá el intento fallido sin romper la inmersión.
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
    return "\n".join(f"- {n.nombre} (actitud: {n.actitud.value}): {n.descripcion}" for n in npcs)
