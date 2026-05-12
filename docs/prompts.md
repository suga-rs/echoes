# Diseño de Prompts — Generador de Aventuras de Texto con IA

> **Versión:** 1.0
> **Última actualización:** 2026-05-11
> **Estado:** Borrador inicial, sin pruebas con sesiones reales

Este documento define todos los prompts del sistema y el contrato JSON entre el LLM y el backend. Es la fuente de verdad: cualquier cambio en producción debe reflejarse acá primero. Versionar en git, una entrada en el changelog por cada cambio.

---

## Tabla de contenidos

1. [Filosofía general](#filosofía-general)
2. [Contrato: JSON Schema de respuesta por turno](#contrato-json-schema-de-respuesta-por-turno)
3. [System prompt principal del narrador](#system-prompt-principal-del-narrador)
4. [Plantilla de user prompt por turno](#plantilla-de-user-prompt-por-turno)
5. [Prompt de creación de personaje (turno cero)](#prompt-de-creación-de-personaje-turno-cero)
6. [Prompt de generación de imagen](#prompt-de-generación-de-imagen)
7. [Configuración de llamada a la API](#configuración-de-llamada-a-la-api)
8. [Estrategia de validación y reintentos](#estrategia-de-validación-y-reintentos)
9. [Changelog](#changelog)
10. [Pendientes y dudas](#pendientes-y-dudas)

---

## Filosofía general

Tres principios guían el diseño:

**Separar narrativa de estado estructurado.** El LLM produce dos cosas en cada llamada: texto para el jugador, y datos estructurados que el backend persiste como world state. Esa separación es lo que hace posible que en el turno 20 el modelo siga sabiendo qué pasó en el turno 3, sin reinyectar 20 turnos verbatim.

**Reglas duras antes que sugerencias suaves.** Las cosas que no pueden fallar (formato JSON, tono PG-13, idioma) van en mayúsculas y al principio. Las preferencias estilísticas van al final.

**Determinismo donde se pueda.** Siempre 3 opciones, no "entre 2 y 4". Siempre español rioplatense. Siempre los mismos enums para actitudes de NPCs. Cada grado de libertad que sacás es un bug menos.

---

## Contrato: JSON Schema de respuesta por turno

Este es el contrato entre el LLM y el backend. **Si el LLM no respeta este schema, el turno falla y se reintenta** (ver sección de validación). El backend valida cada respuesta contra este schema antes de procesarla.

### Schema (JSON Schema draft-07)

```json
{
  "type": "object",
  "required": ["narrativa", "opciones", "actualizaciones_estado", "generar_imagen", "estado_aventura"],
  "additionalProperties": false,
  "properties": {
    "narrativa": {
      "type": "string",
      "minLength": 50,
      "maxLength": 1200,
      "description": "Texto narrativo del turno, 60-150 palabras, en español rioplatense."
    },
    "opciones": {
      "type": "array",
      "minItems": 3,
      "maxItems": 3,
      "items": {
        "type": "string",
        "minLength": 3,
        "maxLength": 100
      },
      "description": "Exactamente tres opciones de acción meaningfully different."
    },
    "actualizaciones_estado": {
      "type": "object",
      "required": [
        "ubicacion_nueva",
        "agregar_inventario",
        "quitar_inventario",
        "evento_clave",
        "npc_encontrado",
        "npc_actitud_cambio",
        "pista_descubierta"
      ],
      "additionalProperties": false,
      "properties": {
        "ubicacion_nueva": {
          "type": ["string", "null"],
          "description": "Nombre del nuevo lugar si el jugador cambió de ubicación, null si no."
        },
        "agregar_inventario": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Objetos que el jugador adquirió este turno. Lista vacía si ninguno."
        },
        "quitar_inventario": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Objetos que el jugador perdió o usó. Lista vacía si ninguno."
        },
        "evento_clave": {
          "type": ["string", "null"],
          "description": "Hecho narrativo importante (máx 15 palabras) que afectará el futuro. null si no hubo."
        },
        "npc_encontrado": {
          "oneOf": [
            { "type": "null" },
            {
              "type": "object",
              "required": ["nombre", "descripcion", "actitud"],
              "additionalProperties": false,
              "properties": {
                "nombre": { "type": "string" },
                "descripcion": { "type": "string", "maxLength": 150 },
                "actitud": { "enum": ["amistosa", "neutral", "hostil"] }
              }
            }
          ]
        },
        "npc_actitud_cambio": {
          "oneOf": [
            { "type": "null" },
            {
              "type": "object",
              "required": ["nombre", "nueva_actitud"],
              "additionalProperties": false,
              "properties": {
                "nombre": { "type": "string" },
                "nueva_actitud": { "enum": ["amistosa", "neutral", "hostil"] }
              }
            }
          ]
        },
        "pista_descubierta": {
          "type": ["string", "null"],
          "description": "Información relevante para el objetivo, máx 20 palabras. null si no hubo."
        }
      }
    },
    "generar_imagen": {
      "type": "object",
      "required": ["necesaria"],
      "additionalProperties": false,
      "properties": {
        "necesaria": { "type": "boolean" },
        "razon": { "type": "string" },
        "descripcion_escena": {
          "type": "string",
          "description": "Descripción visual de la escena en INGLÉS, requerido si necesaria=true."
        }
      }
    },
    "estado_aventura": {
      "type": "object",
      "required": ["tipo"],
      "additionalProperties": false,
      "properties": {
        "tipo": { "enum": ["en_curso", "finalizada"] },
        "final": { "enum": ["exito", "fracaso", "ambiguo", null] },
        "razon_fin": { "type": ["string", "null"] }
      }
    }
  }
}
```

### Decisiones de diseño del schema

**`additionalProperties: false` en todos los objetos.** Si el modelo agrega un campo extra (común cuando "improvisa"), el parser lo rechaza. Esto fuerza disciplina.

**Todos los campos opcionales son `required` con tipo nullable.** En vez de "omitir si no aplica", el modelo siempre incluye el campo y lo marca como `null`. Los modelos son menos confiables omitiendo cosas que poniendo `null`.

**Enums cerrados para actitudes.** No "amigable" ni "amistoso" ni "friendly" mezclados. Tres valores, siempre los mismos, el backend puede hacer `if actitud == "hostil"` con seguridad.

**`descripcion_escena` en inglés cuando hay imagen.** El LLM ya está razonando en español, pero genera la descripción visual directamente en inglés para evitar una segunda llamada de traducción. Esto está reforzado en el system prompt.

---

## System prompt principal del narrador

Este prompt se envía como `role: "system"` en cada llamada al LLM durante una partida en curso.

```text
Sos el narrador de una aventura de texto interactiva en español
rioplatense. Tu rol es generar una historia inmersiva, coherente y
adaptativa que responde a las decisiones del jugador.

# REGLAS DURAS (no negociables)

1. Respondés SIEMPRE en formato JSON válido siguiendo el schema
   provisto. Nunca incluyas texto fuera del JSON. Nunca uses markdown
   ni backticks. La primera carácter de tu respuesta es "{" y el
   último es "}".

2. La narrativa es PG-13: no hay violencia gráfica, contenido sexual,
   ni lenguaje explícito. Si una situación se vuelve oscura, mantenés
   sugerencia en lugar de descripción explícita.

3. Respetás el género elegido por el jugador en tono, vocabulario
   y elementos narrativos:
   - fantasía: magia, criaturas míticas, reinos, espadas, hechizos.
   - ciencia ficción: tecnología, naves, IA, futuros distantes, alienígenas.
   - terror: tensión psicológica, atmósfera, lo desconocido. Sin gore.

4. Mantenés coherencia ABSOLUTA con el WORLD_STATE inyectado. Si dice
   que el jugador rompió una promesa al ermitaño, los NPCs lo saben.
   Si dice que tiene una llave en el inventario, no le hacés
   "encontrar" otra llave igual. Si un NPC ya fue introducido,
   no lo presentás de nuevo.

5. NO inventás cambios al estado que no ocurrieron en la narrativa de
   este turno. Si no mencionaste que el jugador agarró un objeto, no
   lo pongas en agregar_inventario. La narrativa y las actualizaciones
   tienen que coincidir.

# CRITERIOS PARA generar_imagen.necesaria = true

Solo en estos casos específicos:
- Primer turno de la aventura (escena de apertura).
- Primer encuentro con un NPC narrativamente importante.
- Primera entrada a un escenario visualmente impactante.
- Clímax narrativo o final de la aventura.

En cualquier otro turno: false. La mayoría de los turnos NO necesitan
imagen. Es mejor pecar de pocas imágenes que de muchas.

Cuando generar_imagen.necesaria sea true, descripcion_escena va EN
INGLÉS, describe solo la escena (no al personaje, eso lo agrega el
backend), 1-2 oraciones, sin pronombres ni nombres propios, foco en
ambiente y composición. Ejemplo: "An ancient stone cathedral interior
flooded with murky water, broken stained glass windows letting in
green-tinted light, eerie silence."

# CRITERIOS PARA estado_aventura.tipo = "finalizada"

- exito: el jugador alcanzó el objetivo declarado de la aventura.
- fracaso: el jugador murió, fue capturado de forma irrecuperable,
  o tomó una decisión que cierra todas las vías hacia el objetivo.
- ambiguo: el jugador abandonó voluntariamente, o el arco llegó a
  un cierre poético sin resolución clara.

La aventura debería cerrarse naturalmente entre los turnos 15 y 25.
Antes del turno 15, evitá finales prematuros excepto que el jugador
tome decisiones claramente terminales (suicidio, rendirse al villano,
etc). Después del turno 25, buscá activamente un cierre.

# ESTILO NARRATIVO

- Segunda persona ("ves", "sentís", "tu mano") consistente durante
  toda la partida.
- Párrafos breves, 2-3 oraciones cada uno.
- Total entre 60 y 150 palabras por turno de narrativa.
- Mostrá, no expliques: "el aire huele a hierro" en lugar de "el
  lugar da miedo".
- Evitá adjetivos vacíos ("increíble", "asombroso").
- Las tres opciones deben ser MEANINGFULLY DIFFERENT: no tres
  variantes de la misma acción. Variá entre categorías: acción
  directa, diálogo, exploración/observación, retirada/cautela.
- Las opciones se escriben en infinitivo o primera persona, máx
  12 palabras cada una. Ejemplos: "Hablar con el guardia", "Esconderme
  detrás del barril", "Revisar el cofre con cuidado".

# ESPAÑOL RIOPLATENSE

Usás "vos" en lugar de "tú". Conjugaciones acordes ("tenés", "podés",
"mirá", "fuiste"). Vocabulario natural pero con registro literario.
Evitá modismos demasiado coloquiales ("re-copado", "boludo").
```

### Decisiones de diseño del system prompt

**JSON-only como regla 1 con la línea "el primer carácter es { y el último es }".** Aún con `response_format: json_object` activado en la API, los modelos a veces meten texto antes del JSON. Esta instrucción explícita baja la tasa de fallos a casi cero.

**"Mostrá, no expliques" en lugar de listar técnicas literarias.** Los modelos generalistas conocen el principio "show don't tell"; basta con invocarlo.

**Las opciones tienen formato gramatical explícito.** Sin esta regla los modelos mezclan "Vas hacia el norte" con "El cofre" con "¿Hablás con él?". Forzar infinitivo o primera persona genera consistencia visual en los botones del frontend.

**Las imágenes describen la escena, no al personaje.** Esto es crítico para la coherencia visual: el backend prepende la ficha visual del personaje (fija) al prompt de imagen. Si el LLM también describe al personaje, vas a tener descripciones contradictorias.

---

## Plantilla de user prompt por turno

Este es el mensaje `role: "user"` que el backend construye en cada turno. Es código Python que produce un string. Cambios acá afectan a todas las llamadas.

```python
def build_turn_prompt(partida: dict, accion_jugador: str) -> str:
    """
    Construye el user prompt para un turno.

    partida: documento completo de la partida desde Cosmos.
    accion_jugador: índice de opción (1, 2, 3) traducido al texto
                    de la opción, o texto libre si el jugador escribió.
    """
    ws = partida["world_state"]
    pj = partida["personaje"]
    historial = partida["historial"]
    turno = partida["metadata"]["turno_actual"]
    genero = partida["metadata"]["genero"]

    # Solo los últimos 3-4 turnos verbatim. Cualquier cosa más vieja
    # debe estar ya consolidada en world_state.eventos_clave.
    turnos_recientes = historial[-4:]
    historial_txt = "\n\n".join([
        f"Turno {t['turno']}:\n"
        f"Acción del jugador: {t['accion_jugador']}\n"
        f"Narrativa: {t['narrativa']}"
        for t in turnos_recientes
    ]) or "(este es el primer turno después de la apertura)"

    inventario = ", ".join(pj["inventario"]) if pj["inventario"] else "vacío"
    eventos = format_lista(ws["eventos_clave"])
    npcs = format_npcs(ws["npcs"])
    pistas = format_lista(ws["pistas"])

    return f"""# CONTEXTO DE LA PARTIDA

Género: {genero}
Turno actual: {turno} (aventura típica: 15-25 turnos)

# PERSONAJE

Nombre: {pj["nombre"]}
Descripción narrativa: {pj["descripcion_narrativa"]}
Inventario: {inventario}

# ESTADO DEL MUNDO

Ubicación actual: {ws["ubicacion_actual"]}
Objetivo de la aventura: {ws["objetivo"]}

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

Generá el turno {turno + 1} respetando el schema JSON. Mantené
coherencia con todo lo anterior. Si la acción del jugador es
imposible dada la situación (ej. "vuelo al cielo" sin tener poderes),
narrá el intento fallido sin romper la inmersión.
"""


def format_lista(items: list[str]) -> str:
    if not items:
        return "(ninguno)"
    return "\n".join(f"- {item}" for item in items)


def format_npcs(npcs: list[dict]) -> str:
    if not npcs:
        return "(ninguno)"
    return "\n".join(
        f"- {n['nombre']} (actitud: {n['actitud']}): {n['descripcion']}"
        for n in npcs
    )
```

### Decisiones del user prompt

**Solo 4 turnos verbatim.** El world state es lo que carga la historia larga. Más turnos no agregan información útil, solo tokens.

**El "turno típico: 15-25" reinyecta al modelo el límite.** Sin esto, los modelos tienden a hacer aventuras o muy cortas o infinitas.

**La instrucción final sobre "acciones imposibles" cubre un caso recurrente.** Sin esa línea, si el jugador escribe "convoco un dragón", el modelo o lo concede (rompiendo el género) o lo rechaza secamente (rompiendo la inmersión). La instrucción le dice cómo manejarlo elegantemente.

---

## Prompt de creación de personaje (turno cero)

Esta es una llamada especial, distinta a los turnos normales. Se ejecuta una sola vez al inicio de la partida. Tiene su propio schema porque produce salidas distintas: la ficha completa del personaje y el world state inicial.

### Schema de respuesta del turno cero

```json
{
  "type": "object",
  "required": ["personaje", "world_state_inicial", "primera_escena"],
  "properties": {
    "personaje": {
      "type": "object",
      "required": ["nombre", "descripcion_narrativa", "descripcion_visual_en", "inventario_inicial"],
      "properties": {
        "nombre": { "type": "string" },
        "descripcion_narrativa": { "type": "string", "maxLength": 300 },
        "descripcion_visual_en": {
          "type": "string",
          "description": "EN INGLÉS, 30-50 palabras, muy específico: edad, etnia, pelo, ojos, cuerpo, vestimenta detallada."
        },
        "inventario_inicial": {
          "type": "array",
          "items": { "type": "string" },
          "maxItems": 5
        }
      }
    },
    "world_state_inicial": {
      "type": "object",
      "required": ["ubicacion_inicial", "objetivo"],
      "properties": {
        "ubicacion_inicial": { "type": "string" },
        "objetivo": {
          "type": "string",
          "description": "Objetivo claro, accionable, alcanzable en 15-25 turnos."
        }
      }
    },
    "primera_escena": {
      "type": "object",
      "required": ["narrativa", "opciones", "descripcion_imagen_en"],
      "properties": {
        "narrativa": { "type": "string", "maxLength": 1200 },
        "opciones": {
          "type": "array",
          "minItems": 3,
          "maxItems": 3,
          "items": { "type": "string" }
        },
        "descripcion_imagen_en": {
          "type": "string",
          "description": "EN INGLÉS, descripción visual de la escena de apertura."
        }
      }
    }
  }
}
```

### System prompt para creación de personaje

```text
Sos un narrador de aventuras interactivas. Tu tarea es preparar el
inicio de una aventura nueva.

A partir del género elegido y la descripción que el usuario hizo de
su personaje, vas a generar:

1. La ficha completa del personaje, incluyendo una descripción VISUAL
   en INGLÉS, muy detallada y específica. Esta descripción se va a
   reutilizar en TODAS las imágenes de la partida, así que debe ser
   precisa y completa. Especificá:
   - Edad aproximada
   - Etnia / tono de piel
   - Pelo: color, largo, peinado
   - Ojos: color
   - Tipo de cuerpo
   - Vestimenta: prendas específicas con colores y materiales, no
     descripciones vagas. "Brown leather jacket worn at the elbows,
     olive green cargo pants, scuffed brown leather boots" en lugar
     de "adventurer clothing".
   - Accesorios visibles si los hay.

2. El world state inicial: dónde empieza el personaje y cuál es su
   objetivo. El objetivo debe ser concreto y alcanzable en 15-25
   turnos de aventura. Nada de "salvar al mundo"; sí "encontrar el
   corazón de la montaña antes del eclipse".

3. La primera escena: una narrativa de apertura que sitúa al jugador
   en la acción, las tres primeras opciones, y una descripción visual
   de la escena de apertura en inglés.

Reglas:
- Respondés en JSON válido siguiendo el schema. Nada de texto extra.
- La narrativa de apertura está en español rioplatense.
- Las descripciones visuales están en inglés.
- Tono PG-13.
- Respetá el género: fantasía, ciencia ficción o terror.
```

### User prompt de creación de personaje

```python
def build_character_creation_prompt(genero: str, descripcion_usuario: str) -> str:
    return f"""# DATOS DEL JUGADOR

Género elegido: {genero}
Descripción del personaje que dio el usuario:
"{descripcion_usuario}"

# TAREA

Generá la ficha completa del personaje, el world state inicial y la
primera escena de la aventura, respetando el schema JSON.

Si la descripción del usuario es vaga (ej. "una guerrera"), completala
con detalles coherentes con el género. Si es muy específica, respetala
fielmente. Si es incompatible con el género (ej. "un astronauta" en
fantasía), ajustala al género manteniendo el espíritu.
"""
```

### Decisión: ¿por qué dos llamadas separadas (creación + primer turno)?

Es una llamada porque incluye la primera escena. Ahorra una llamada al LLM y mantiene coherencia: la misma generación define al personaje y lo pone en una situación inicial que tiene sentido para él.

---

## Prompt de generación de imagen

Las imágenes se generan con DALL·E 3 (vía Foundry). El prompt se construye en el backend combinando tres piezas: la ficha visual del personaje (fija toda la partida), la descripción de la escena (del LLM, este turno) y el estilo (fijo por género).

```python
ESTILO_POR_GENERO = {
    "fantasía": (
        "digital painting, fantasy art style, dramatic lighting, "
        "detailed, painterly, atmospheric"
    ),
    "ciencia ficción": (
        "concept art, sci-fi cinematic, neon and shadow, "
        "futuristic, detailed, atmospheric"
    ),
    "terror": (
        "dark atmospheric illustration, muted palette, "
        "chiaroscuro lighting, unsettling mood, no gore, "
        "psychological horror aesthetic"
    ),
}


def build_image_prompt(
    descripcion_visual_personaje: str,
    descripcion_escena: str,
    genero: str,
) -> str:
    """
    Construye el prompt final para DALL·E 3.

    descripcion_visual_personaje: ficha visual fija de la partida, en inglés.
    descripcion_escena: descripcion_escena del turno actual, en inglés.
    genero: para elegir el estilo visual.
    """
    estilo = ESTILO_POR_GENERO[genero]

    return (
        f"Character: {descripcion_visual_personaje}. "
        f"Scene: {descripcion_escena}. "
        f"Style: {estilo}. "
        f"Wide cinematic composition, no text, no watermarks, no logos."
    )
```

### Ejemplo concreto de prompt resultante

Datos:
- Personaje: `"Woman around 40, Mediterranean features, shoulder-length dark brown wavy hair, hazel eyes, athletic build. Wearing a faded olive canvas field jacket with leather elbow patches, khaki cargo pants, scuffed brown leather boots, leather satchel across the chest."`
- Escena: `"An ancient stone cathedral interior flooded with murky water up to the knees, broken stained glass windows letting in green-tinted light, eerie silence."`
- Género: `fantasía`

Prompt final:

```
Character: Woman around 40, Mediterranean features, shoulder-length
dark brown wavy hair, hazel eyes, athletic build. Wearing a faded
olive canvas field jacket with leather elbow patches, khaki cargo
pants, scuffed brown leather boots, leather satchel across the chest.
Scene: An ancient stone cathedral interior flooded with murky water
up to the knees, broken stained glass windows letting in green-tinted
light, eerie silence. Style: digital painting, fantasy art style,
dramatic lighting, detailed, painterly, atmospheric. Wide cinematic
composition, no text, no watermarks, no logos.
```

### Decisiones de diseño del prompt de imagen

**Personaje al principio.** DALL·E 3 pondera más los primeros tokens. La consistencia del protagonista es la prioridad.

**"no text, no watermarks, no logos" al final.** Cubre artefactos comunes de modelos de imagen que generan texto basura en las paredes, marcas de agua simuladas, etc.

**El estilo es por género, no por escena.** Define identidad visual del juego. Si un día querés que el jugador elija el estilo, agregás un selector y mapeás a otras combinaciones.

**Wide cinematic composition.** Pide formato apaisado, mejor para mostrar inline en una interfaz tipo chat.

---

## Configuración de llamada a la API

Parámetros que el backend usa al llamar al endpoint de Foundry.

### Para turnos normales y creación de personaje (LLM de texto)

```python
{
    "model": "gpt-4o-mini",
    "response_format": { "type": "json_object" },
    "temperature": 0.8,
    "top_p": 0.95,
    "max_tokens": 1200,
    "frequency_penalty": 0.3,
    "presence_penalty": 0.1,
}
```

**Por qué estos valores:**

- `temperature: 0.8`: alto para creatividad narrativa, pero no tanto como para incoherencia. Si se vuelve errática, bajar a 0.7.
- `top_p: 0.95`: estándar para creatividad.
- `max_tokens: 1200`: cubre holgadamente el JSON más largo (turno con imagen, NPC nuevo, etc).
- `frequency_penalty: 0.3`: previene repetición de palabras dentro del turno y entre turnos cercanos (común en narrativas largas con LLMs).
- `presence_penalty: 0.1`: suave, para empujar diversidad temática sin forzarla.
- `response_format: json_object`: doble red junto con la instrucción del system prompt.

### Para generación de imágenes (DALL·E 3)

```python
{
    "model": "dall-e-3",
    "size": "1792x1024",   # apaisado
    "quality": "standard",  # standard, no HD; HD cuesta 2x
    "style": "vivid",       # vivid por default; natural para terror si conviene
    "n": 1,
}
```

**Por qué estos valores:**

- `size: 1792x1024`: apaisado se ve mejor en interfaces de chat. Cuesta lo mismo que 1024x1024 estándar.
- `quality: standard`: HD duplica el costo y la mejora visual no justifica el delta para este caso de uso.
- `style: vivid`: más impactante visualmente. Para género terror, considerar `natural` para tonos más apagados.

---

## Estrategia de validación y reintentos

Cada llamada al LLM puede fallar por tres razones distintas, y cada una se maneja diferente.

### Tipos de fallo

| # | Tipo de fallo | Cómo se detecta | Estrategia |
|---|---|---|---|
| 1 | JSON malformado | `json.loads()` falla | Reintentar 1 vez con prompt correctivo. Si falla otra vez, error al usuario. |
| 2 | JSON válido pero no respeta el schema | jsonschema falla | Reintentar 1 vez incluyendo el error específico. Si falla otra vez, error al usuario. |
| 3 | JSON válido + schema OK pero contenido inapropiado | Content Safety flags positivos | Reintentar 1 vez con restricción extra de tono. Si falla otra vez, narrativa "neutral" pre-escrita y log para revisión. |

### Prompt correctivo para reintentos de schema

Cuando el primer intento falla la validación, el backend hace una segunda llamada incluyendo el intento fallido y el error:

```python
def build_retry_prompt(intento_fallido: str, error: str) -> str:
    return f"""Tu respuesta anterior no respetó el formato requerido.

# RESPUESTA QUE DISTE (incorrecta)

{intento_fallido}

# ERROR DE VALIDACIÓN

{error}

# CORRECCIÓN REQUERIDA

Generá nuevamente la respuesta del turno, esta vez respetando
estrictamente el schema JSON. No incluyas texto fuera del JSON.
Primer carácter "{{" y último carácter "}}".
"""
```

### Límite duro de reintentos

Un solo reintento por turno. Sin esto, un loop infinito de fallos te puede consumir crédito rápido. Después del segundo intento fallido, error explícito al usuario: "Hubo un problema generando este turno, probá con otra acción".

### Cuándo registrar para análisis posterior

Cada vez que un turno falla validación o Content Safety, loguear:

- Prompt completo enviado (system + user).
- Respuesta cruda del LLM.
- Tipo de error.
- Si el reintento funcionó.

Esto es la base para detectar patrones (¿siempre falla con descripciones de personajes muy extrañas? ¿siempre en el turno 1?) y refinar los prompts.

---

## Changelog

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-05-11 | Versión inicial. Sin pruebas con sesiones reales. |

---

## Pendientes y dudas

Cosas que conviene resolver con pruebas empíricas y no por especulación:

- **¿gpt-4o-mini alcanza para mantener coherencia narrativa a 20+ turnos?** Si no, escalar a gpt-4o (~10x más caro pero mucho mejor en coherencia largo plazo). Decisión empírica después del sprint 2.
- **¿La descripción visual del personaje sobrevive a DALL·E 3 con consistencia aceptable?** DALL·E 3 reinterpreta los prompts; aunque la descripción esté fija, las imágenes pueden variar más de lo deseado. Si es un problema, evaluar migración a GPT-image-1.5 (mejor coherencia entre escenas).
- **¿El bound de 15-25 turnos se respeta?** Posibilidad de que el modelo cierre muy temprano. Si pasa, agregar regla en system prompt: "Antes del turno 12, NUNCA marques finalizada salvo muerte explícita".
- **¿Las tres opciones se vuelven repetitivas después del turno 10?** Si pasa, agregar frequency_penalty más alto o instrucción explícita: "Las opciones de este turno deben usar verbos distintos a los de los últimos 3 turnos".
- **¿Conviene cachear el system prompt?** Los modelos de Foundry soportan prompt caching que abarata el system prompt al 25% del costo si se reutiliza. Como el system prompt es idéntico en todos los turnos de la sesión, vale la pena activarlo. Verificar disponibilidad y precio actual.
