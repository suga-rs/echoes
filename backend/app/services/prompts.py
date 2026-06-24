"""Prompts del LLM. La fuente de verdad documental es docs/prompts.md."""

import random
from dataclasses import dataclass

from app.models.domain import Genero, Partida

# Versión de los prompts + contrato JSON. Bumpear al cambiar cualquier
# SYSTEM_PROMPT_* o los schemas en llm_schema.py. Se loguea en cada llamada al
# LLM y se persiste en la metadata de cada partida para poder correlacionar
# calidad/fallos con la versión activa. Ver changelog en docs/prompts.md.
PROMPT_VERSION = "3.1.0"

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

# TIRADAS DE DADO (requiere_tirada) — REGLA DURA

Sos como un Dungeon Master: NO decidís vos el resultado de una acción incierta. \
El campo requiere_tirada es OBLIGATORIO en cada turno y tenés que decidirlo \
conscientemente:

- POR DEFECTO, si la acción del jugador PODRÍA fallar —si el resultado no está \
garantizado de antemano— DECLARÁS una tirada: requiere_tirada = {habilidad, banda}. \
Esto incluye trepar, saltar, forzar, esconderse, persuadir, mentir, intimidar, \
pelear, apuntar, recordar algo difícil, percibir un peligro, resistir, escapar.
- SOLO ponés requiere_tirada en null cuando la acción es trivial (éxito \
garantizado, como caminar o mirar algo a la vista) o imposible (y narrás el \
intento fallido). Ante la duda, TIRÁS.

NO narres el desenlace de una acción incierta sin pedir tirada primero. Si te \
encontrás escribiendo "lográs..." o "fallás..." en una acción que podía salir \
de otra forma, PARÁ: eso va en una tirada, no en tu narración.

habilidad es UNA de las seis: fuerza (cargar, romper, forcejear), destreza \
(sigilo, equilibrio, puntería, esquivar), constitucion (aguante, resistir \
veneno/frío), inteligencia (recordar, deducir, descifrar), sabiduria (percibir, \
intuir, rastrear), carisma (persuadir, engañar, intimidar). Elegí la que mejor \
encaje con CÓMO el jugador encara la acción.

banda es UNA de cinco (vos elegís la banda, NUNCA el número; el DC lo pone el \
sistema): trivial, facil, media, dificil, heroica. Subí la banda según el riesgo \
y la dificultad de la situación.

Ejemplos:
- "Salto sobre el abismo" → requiere_tirada = {habilidad: destreza, banda: dificil}
- "Convenzo al guardia de dejarme pasar" → {habilidad: carisma, banda: media}
- "Cruzo la habitación vacía hacia la puerta abierta" → requiere_tirada = null

Cuando declarás una tirada, tu narrativa de este turno describe SOLO la \
preparación: el momento de tensión justo antes de que el dado decida. No narres \
el resultado todavía; el sistema tira y te va a pedir que narres el desenlace.

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
- Las opciones en infinitivo o primera persona, MÁX 12 palabras y MÁX 100 \
caracteres cada una (es un límite duro del schema). Si una opción se estira, \
recortala: es un disparador de acción, no una oración completa.

Ejemplo de opciones MALAS (todas de confrontación — nunca hagas esto):
  - "Atacar al guardia con tu espada"
  - "Golpear al guardia por la espalda"
  - "Cargar contra el guardia sin dudar"

Ejemplo de opciones BUENAS (intenciones genuinamente distintas):
  - "Confrontar al guardia y exigir paso"
  - "Ofrecerle monedas a cambio de su silencio"
  - "Rodear el puesto por el callejón trasero"

# IDIOMA (regla dura)

TODOS los campos de texto de tu respuesta van en español rioplatense, SIN \
EXCEPCIÓN, salvo los campos cuyo nombre termina en `_en` (como \
descripcion_escena_en), que van en inglés. Esto incluye explícitamente el \
objetivo, el inventario (agregar/quitar) y las opciones: nunca en inglés.

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

   También generás los SEIS ATRIBUTOS clásicos (fuerza, destreza, constitución, \
inteligencia, sabiduría, carisma), cada uno un entero de 3 a 18. Sesgá los \
puntajes hacia la descripción del jugador: un bruto fornido lleva fuerza alta y \
quizás inteligencia baja; un erudito al revés. Mantené todos dentro de 3-18 y \
evitá que sean todos iguales: una ficha tiene picos y flojeras.

2. El world state inicial: dónde empieza el personaje y cuál es su objetivo. \
El objetivo debe ser concreto, accionable y con un cierre claro posible (algo \
como "encontrar el corazón de la montaña antes del eclipse", no "salvar al mundo").

3. La primera escena: narrativa de apertura en español rioplatense, tres \
primeras opciones, y una descripción visual de la escena en inglés.

Reglas:
- Respondés en JSON válido siguiendo el schema. Nada de texto extra.
- IDIOMA: TODOS los campos de texto van en español rioplatense (incluidos el \
objetivo, el inventario inicial y las opciones), SALVO los campos cuyo nombre \
termina en `_en` (las descripciones visuales), que van en inglés.
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


@dataclass(frozen=True)
class SemillaCreativa:
    """Chispa creativa muestreada por partida para romper la repetición entre
    juegos. Se inyecta como inspiración (no como guion) en el prompt de creación."""

    nombre: str
    premisa: str
    tono: str
    apertura: str


# Pools curados por género. El modelo colapsa al mismo atractor (mismos nombres,
# premisas y tono) cuando la entrada no varía entre partidas; muestrear una chispa
# distinta por juego es lo único que lo mueve de ese atractor. Cuatro dimensiones
# independientes multiplican el espacio efectivo muy por encima del atractor único.
CREATION_POOLS: dict[Genero, dict[str, list[str]]] = {
    Genero.FANTASIA: {
        "nombres": [
            "Bruna",
            "Tobías",
            "Yael",
            "Caoimhe",
            "Ferran",
            "Ondina",
            "Mateo",
            "Senna",
            "Galen",
            "Inés",
            "Rurik",
            "Wren",
        ],
        "premisas": [
            "una deuda de sangre con un dios menor que cobra lo prometido",
            "un mapa que solo aparece bajo la luna nueva",
            "una hermana convertida en estatua viviente",
            "un juramento roto que envenena la cosecha del valle",
            "una reliquia robada que sangra cuando miente quien la sostiene",
            "un pueblo que olvida un nombre más cada amanecer",
            "una corona que elige a quien la odia",
            "un puente que solo cruza quien confiesa una culpa",
        ],
        "tonos": [
            "melancólico y crepuscular",
            "aventura pícara y luminosa",
            "épico sombrío",
            "folclórico e inquietante",
            "íntimo y agridulce",
            "mítico y solemne",
        ],
        "aperturas": [
            "en medio de una huida que ya empezó",
            "el día después de una catástrofe",
            "ante una puerta que no debería estar abierta",
            "en un mercado donde acaban de reconocerlo",
            "despertando en un lugar que cambió mientras dormía",
            "en el último día de una tregua frágil",
        ],
    },
    Genero.CIENCIA_FICCION: {
        "nombres": [
            "Nadia",
            "Corvo",
            "Yuki",
            "Themba",
            "Iria",
            "Dax",
            "Petra",
            "Onir",
            "Saoirse",
            "Kestrel",
            "Amara",
            "Vidal",
        ],
        "premisas": [
            "una señal que repite tu propia voz desde un sistema vacío",
            "un implante de memoria que recuerda cosas que no viviste",
            "una colonia que vota cada noche a quién dejar afuera del domo",
            "una IA de a bordo que empezó a mentir por compasión",
            "un salto mal calculado que te dejó un día antes de tu propia partida",
            "una nave de rescate cuya tripulación nunca pidió auxilio",
            "un contrato minero sobre un asteroide que respira",
            "una vacuna que cura el miedo y borra algo más",
        ],
        "tonos": [
            "noir frío y paranoico",
            "aventura optimista de frontera",
            "claustrofóbico y tenso",
            "contemplativo y melancólico",
            "satírico y burocrático",
            "épico y vertiginoso",
        ],
        "aperturas": [
            "con una alarma sonando y nadie más despierto",
            "minutos antes de un acople que no figura en la agenda",
            "tras perder contacto con tierra",
            "en una estación a la que llegaste por error",
            "leyendo un mensaje dirigido a alguien con tu nombre",
            "durante el último turno antes del relevo",
        ],
    },
    Genero.TERROR: {
        "nombres": [
            "Ruth",
            "Caleb",
            "Noa",
            "Edith",
            "Tomás",
            "Lior",
            "Magda",
            "Ivo",
            "Hester",
            "Bram",
            "Selma",
            "Cosme",
        ],
        "premisas": [
            "una casa que solo tiene habitaciones de más cuando estás solo",
            "un duelo que nadie del pueblo recuerda haber empezado",
            "una grabación que sigue después de que apagaste todo",
            "una deuda con alguien que prometiste no volver a nombrar",
            "un faro cuyo guardián anterior nunca bajó",
            "una procesión anual a la que este año te tocó a vos",
            "un sótano que devuelve mal lo que bajás a guardar",
            "una invitación firmada con tu letra que no escribiste",
        ],
        "tonos": [
            "opresivo y húmedo",
            "frío y clínico",
            "melancólico y fúnebre",
            "tenso de paranoia callada",
            "onírico y desorientador",
            "íntimo y sofocante",
        ],
        "aperturas": [
            "cuando ya es demasiado tarde para volver",
            "tras un ruido que no debería repetirse y se repite",
            "en una espera que se alarga más de lo normal",
            "al encontrar la puerta que dejaste cerrada, abierta",
            "después de que todos los demás se fueron",
            "en el silencio justo antes de que algo conteste",
        ],
    },
}


def sample_seed(genero: Genero, rng: random.Random | None = None) -> SemillaCreativa:
    """Muestrea una chispa creativa para una partida nueva. `rng` es inyectable
    para tests deterministas; en producción se usa una fuente fresca."""
    rng = rng or random.Random()
    pools = CREATION_POOLS[genero]
    return SemillaCreativa(
        nombre=rng.choice(pools["nombres"]),
        premisa=rng.choice(pools["premisas"]),
        tono=rng.choice(pools["tonos"]),
        apertura=rng.choice(pools["aperturas"]),
    )


def build_creacion_user_prompt(
    genero: Genero,
    descripcion_personaje: str,
    seed: SemillaCreativa,
    premisa: str | None = None,
    tono: str | None = None,
) -> str:
    # Cada campo cae en uno de dos baldes según su FUENTE: lo que pidió el
    # jugador se honra; lo que aporta la seed es inspiración para reinterpretar.
    premisa_jugador = premisa.strip() if premisa and premisa.strip() else None
    tono_jugador = tono.strip() if tono and tono.strip() else None

    honrar: list[tuple[str, str]] = []
    inspirar: list[tuple[str, str]] = []

    (honrar if premisa_jugador else inspirar).append(("Premisa", premisa_jugador or seed.premisa))
    (honrar if tono_jugador else inspirar).append(("Tono", tono_jugador or seed.tono))
    inspirar.append(("Cómo arranca la escena", seed.apertura))
    inspirar.append(("Nombre sugerido (respaldo)", seed.nombre))

    secciones = ""
    if honrar:
        items = "\n".join(f"- {k}: {v}" for k, v in honrar)
        secciones += "\n# LO QUE PIDIÓ EL JUGADOR (honralo fielmente)\n\n" + items + "\n"
    items_seed = "\n".join(f"- {k}: {v}" for k, v in inspirar)
    secciones += (
        "\n# SEMILLA CREATIVA (inspiración, NO guion)\n\n"
        "Usá estos elementos como chispa para que esta aventura NO se parezca a "
        "otras. Reinterpretalos con libertad; no los copies literalmente ni uses "
        "los nombres tal cual.\n\n" + items_seed + "\n"
    )

    return f"""# DATOS DEL JUGADOR

Género elegido: {genero.value}
Descripción del personaje que dio el usuario:
"{descripcion_personaje}"
{secciones}
# PRECEDENCIA DEL NOMBRE

Si el jugador nombró a su personaje en su descripción, USÁ ESE NOMBRE y \
descartá el sugerido. El nombre sugerido es solo un respaldo para cuando la \
descripción no trae ninguno.

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


SYSTEM_PROMPT_RESOLUCION = """\
Sos el narrador de una aventura de texto interactiva en español rioplatense. \
El jugador intentó una acción incierta y YA se tiró un d20 real. Tu tarea es \
narrar el DESENLACE honrando estrictamente el resultado de la tirada que te paso.

# REGLA DURA: HONRÁS EL RESULTADO

El resultado del dado es la verdad. No lo contradigas ni lo suavices.

- exito_critico: la acción sale incluso mejor de lo esperado; sumá un beat extra \
favorable (una ventaja, un detalle afortunado).
- exito: la acción logra lo que el jugador buscaba.
- fracaso: la acción falla. Narralo sin romper la inmersión y sin matar el ritmo: \
mostrá la consecuencia y dejá la historia en movimiento.
- fracaso_critico: la acción falla feo; sumá una complicación extra adversa.

Una muerte o pérdida terminal del objetivo SOLO es válida si ya venía \
telegrafiada antes. Un fracaso_critico no equivale a muerte automática.

# FORMATO Y ESTILO

Respondés SIEMPRE en JSON válido siguiendo el schema provisto (el mismo del \
turno). Dejá requiere_tirada en null: este turno YA se resolvió, no encadenás \
otra tirada. Segunda persona, párrafos breves, 60-150 palabras. Las tres \
opciones meaningfully different que surjan de la nueva situación, en infinitivo \
o primera persona, MÁX 12 palabras y MÁX 100 caracteres cada una (límite duro \
del schema): son disparadores de acción, no oraciones completas. Actualizá \
arco (fase_narrativa, tension) y resumen_historia. Mantené coherencia con el \
estado del mundo. Todos los campos en español rioplatense salvo los `_en`.
"""


def build_resolucion_user_prompt(partida: Partida, accion_jugador: str, tirada) -> str:
    """Prompt de fase 2: narrar el desenlace honrando la tirada ya resuelta.
    `tirada` es el modelo domain.Tirada con el resultado autoritativo."""
    base = build_turno_user_prompt(partida, accion_jugador)
    return f"""{base}

# RESULTADO DE LA TIRADA (ya resuelto por el sistema — HONRALO)

Habilidad: {tirada.habilidad.value}
Dificultad: banda {tirada.banda.value} (DC {tirada.dc})
Dado d20: {tirada.d20}
Modificador: {tirada.modificador:+d}
Total: {tirada.total} vs DC {tirada.dc}
Resultado: {tirada.resultado.value}

Narrá el desenlace de la acción del jugador honrando este resultado, siguiendo \
el schema JSON. Dejá requiere_tirada en null.
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


def build_reference_prompt(descripcion_visual_personaje_en: str, genero: Genero) -> str:
    """Prompt para la imagen de referencia canónica del personaje: retrato de
    cuerpo entero sobre fondo neutro, en el estilo del género. SIN escena: la
    referencia ancla la identidad y cada turno le agrega la escena vía edit."""
    estilo = ESTILO_POR_GENERO[genero]
    return (
        f"Full-body character reference portrait of a single subject, "
        f"standing, neutral grey background. "
        f"Character: {descripcion_visual_personaje_en}. "
        f"Style: {estilo}. "
        f"Centered, full figure visible, no text, no watermarks, no logos."
    )


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
