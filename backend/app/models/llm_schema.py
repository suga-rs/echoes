"""Schemas de respuesta del LLM y su versión Pydantic."""

from typing import Any

from pydantic import BaseModel, Field

TURNO_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "narrativa",
        "opciones",
        "actualizaciones_estado",
        "generar_imagen",
        "estado_aventura",
        "arco",
        "resumen_historia",
        "requiere_tirada",
        "consecuencia",
    ],
    "additionalProperties": False,
    "properties": {
        "narrativa": {"type": "string", "minLength": 50, "maxLength": 1500},
        "opciones": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "string",
                "minLength": 3,
                "maxLength": 100,
                "description": "En español rioplatense (es-AR).",
            },
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
                "pista_descubierta",
            ],
            "additionalProperties": False,
            "properties": {
                "ubicacion_nueva": {"type": ["string", "null"]},
                "agregar_inventario": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "description": "En español rioplatense (es-AR).",
                    },
                },
                "quitar_inventario": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "description": "En español rioplatense (es-AR).",
                    },
                },
                "evento_clave": {"type": ["string", "null"]},
                "npc_encontrado": {
                    "oneOf": [
                        {"type": "null"},
                        {
                            "type": "object",
                            "required": [
                                "nombre",
                                "descripcion",
                                "actitud",
                                "descripcion_visual_en",
                            ],
                            "additionalProperties": False,
                            "properties": {
                                "nombre": {"type": "string"},
                                "descripcion": {"type": "string", "maxLength": 200},
                                "actitud": {"enum": ["amistosa", "neutral", "hostil"]},
                                "descripcion_visual_en": {
                                    "type": "string",
                                    "description": (
                                        "Descripción VISUAL canónica del NPC, en INGLÉS, "
                                        "detallada (edad, etnia, pelo, ojos, cuerpo, "
                                        "vestimenta con colores/materiales, accesorios). "
                                        "Se persiste una sola vez y se reutiliza en cada "
                                        "imagen donde el NPC aparece."
                                    ),
                                },
                            },
                        },
                    ]
                },
                "npc_actitud_cambio": {
                    "oneOf": [
                        {"type": "null"},
                        {
                            "type": "object",
                            "required": ["nombre", "nueva_actitud"],
                            "additionalProperties": False,
                            "properties": {
                                "nombre": {"type": "string"},
                                "nueva_actitud": {"enum": ["amistosa", "neutral", "hostil"]},
                            },
                        },
                    ]
                },
                "pista_descubierta": {"type": ["string", "null"]},
            },
        },
        "generar_imagen": {
            "type": "object",
            "required": ["necesaria", "descripcion_escena_en"],
            "additionalProperties": False,
            "properties": {
                "necesaria": {"type": "boolean"},
                "razon": {"type": "string"},
                "descripcion_escena_en": {"type": "string"},
                "npcs_en_escena": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Nombres de NPCs YA conocidos que están visualmente "
                        "presentes en la escena de este turno. Referenciá nombres "
                        "existentes (no redescribas su aspecto). Vacío si no hay NPCs."
                    ),
                },
            },
        },
        "estado_aventura": {
            "type": "object",
            "required": ["tipo"],
            "additionalProperties": False,
            "properties": {
                "tipo": {"enum": ["en_curso", "finalizada"]},
                "final": {"enum": ["exito", "fracaso", "ambiguo", None]},
                "razon_fin": {"type": ["string", "null"]},
            },
        },
        "arco": {
            "type": "object",
            "required": ["fase_narrativa", "tension"],
            "additionalProperties": False,
            "properties": {
                "fase_narrativa": {"enum": ["introduccion", "desarrollo", "climax", "resolucion"]},
                "tension": {"type": "integer", "minimum": 0, "maximum": 10},
            },
        },
        "resumen_historia": {"type": "string", "maxLength": 1500},
        # Fase 1 del turno: el narrador declara una tirada cuando el desenlace es
        # incierto. Opcional (ausente o null = acción trivial/imposible, sin dado).
        # El narrador elige habilidad + banda; NUNCA un DC (lo pone el sistema).
        "requiere_tirada": {
            "oneOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "required": ["habilidad", "banda"],
                    "additionalProperties": False,
                    "properties": {
                        "habilidad": {
                            "enum": [
                                "fuerza",
                                "destreza",
                                "constitucion",
                                "inteligencia",
                                "sabiduria",
                                "carisma",
                            ]
                        },
                        "banda": {"enum": ["trivial", "facil", "media", "dificil", "heroica"]},
                    },
                },
            ]
        },
        # Consecuencia física del turno: daño y/o condición que el sistema aplica.
        # Es INDEPENDIENTE de requiere_tirada: una trampa o veneno ambiental puede
        # dañar sin tirada previa, y un fracaso puede colgar un costo. El narrador
        # declara la BANDA de severidad (nunca PV crudos) y la intención de cura;
        # el sistema es dueño del número. null = el turno no tuvo costo físico.
        "consecuencia": {
            "oneOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "required": [
                        "dano",
                        "condicion_aplicar",
                        "condicion_quitar",
                        "descanso",
                        "curar_pocion",
                    ],
                    "additionalProperties": False,
                    "properties": {
                        "dano": {"enum": ["rasguno", "leve", "grave", "severo", "mortal", None]},
                        "condicion_aplicar": {
                            "oneOf": [
                                {"type": "null"},
                                {
                                    "type": "object",
                                    "required": ["tipo", "efecto", "duracion"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "tipo": {
                                            "enum": [
                                                "envenenado",
                                                "sangrando",
                                                "aturdido",
                                                "exhausto",
                                            ]
                                        },
                                        "efecto": {"enum": ["desventaja", "dano_por_turno"]},
                                        "duracion": {
                                            "oneOf": [
                                                {"type": "integer", "minimum": 1, "maximum": 10},
                                                {"enum": ["hasta_curar", "hasta_evento"]},
                                            ]
                                        },
                                    },
                                },
                            ]
                        },
                        "condicion_quitar": {
                            "enum": [
                                "envenenado",
                                "sangrando",
                                "aturdido",
                                "exhausto",
                                None,
                            ]
                        },
                        "descanso": {"type": "boolean"},
                        "curar_pocion": {"type": ["string", "null"]},
                    },
                },
            ]
        },
    },
}


CREACION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["personaje", "world_state_inicial", "primera_escena"],
    "additionalProperties": False,
    "properties": {
        "personaje": {
            "type": "object",
            "required": [
                "nombre",
                "descripcion_narrativa",
                "descripcion_visual_en",
                "inventario_inicial",
                "atributos",
            ],
            "additionalProperties": False,
            "properties": {
                "nombre": {"type": "string", "minLength": 1, "maxLength": 50},
                "descripcion_narrativa": {"type": "string", "maxLength": 300},
                "descripcion_visual_en": {"type": "string", "minLength": 50},
                "inventario_inicial": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "description": "En español rioplatense (es-AR).",
                    },
                    "maxItems": 5,
                },
                "atributos": {
                    "type": "object",
                    "required": [
                        "fuerza",
                        "destreza",
                        "constitucion",
                        "inteligencia",
                        "sabiduria",
                        "carisma",
                    ],
                    "additionalProperties": False,
                    "properties": {
                        "fuerza": {"type": "integer", "minimum": 3, "maximum": 18},
                        "destreza": {"type": "integer", "minimum": 3, "maximum": 18},
                        "constitucion": {"type": "integer", "minimum": 3, "maximum": 18},
                        "inteligencia": {"type": "integer", "minimum": 3, "maximum": 18},
                        "sabiduria": {"type": "integer", "minimum": 3, "maximum": 18},
                        "carisma": {"type": "integer", "minimum": 3, "maximum": 18},
                    },
                },
            },
        },
        "world_state_inicial": {
            "type": "object",
            "required": ["ubicacion_inicial", "objetivo"],
            "additionalProperties": False,
            "properties": {
                "ubicacion_inicial": {"type": "string"},
                "objetivo": {
                    "type": "string",
                    "description": "En español rioplatense (es-AR).",
                },
            },
        },
        "primera_escena": {
            "type": "object",
            "required": ["narrativa", "opciones", "descripcion_imagen_en"],
            "additionalProperties": False,
            "properties": {
                "narrativa": {"type": "string", "maxLength": 1500},
                "opciones": {
                    "type": "array",
                    "minItems": 3,
                    "maxItems": 3,
                    "items": {
                        "type": "string",
                        "description": "En español rioplatense (es-AR).",
                    },
                },
                "descripcion_imagen_en": {"type": "string"},
            },
        },
    },
}


class GenerarImagen(BaseModel):
    necesaria: bool
    razon: str | None = None
    descripcion_escena_en: str = ""
    npcs_en_escena: list[str] = Field(default_factory=list)


class NPCEncontrado(BaseModel):
    nombre: str
    descripcion: str
    actitud: str
    descripcion_visual_en: str = ""


class NPCCambio(BaseModel):
    nombre: str
    nueva_actitud: str


class ActualizacionesEstado(BaseModel):
    ubicacion_nueva: str | None
    agregar_inventario: list[str] = Field(default_factory=list)
    quitar_inventario: list[str] = Field(default_factory=list)
    evento_clave: str | None
    npc_encontrado: NPCEncontrado | None
    npc_actitud_cambio: NPCCambio | None
    pista_descubierta: str | None


class EstadoAventuraLLM(BaseModel):
    tipo: str
    final: str | None = None
    razon_fin: str | None = None


class ArcoLLM(BaseModel):
    fase_narrativa: str
    tension: int


class RequiereTirada(BaseModel):
    habilidad: str
    banda: str


class CondicionAplicarLLM(BaseModel):
    tipo: str
    efecto: str
    duracion: int | str


class ConsecuenciaLLM(BaseModel):
    dano: str | None = None
    condicion_aplicar: CondicionAplicarLLM | None = None
    condicion_quitar: str | None = None
    descanso: bool = False
    curar_pocion: str | None = None


class TurnoLLMResponse(BaseModel):
    narrativa: str
    opciones: list[str]
    actualizaciones_estado: ActualizacionesEstado
    generar_imagen: GenerarImagen
    estado_aventura: EstadoAventuraLLM
    arco: ArcoLLM
    resumen_historia: str
    requiere_tirada: RequiereTirada | None = None
    consecuencia: ConsecuenciaLLM | None = None


class AtributosLLM(BaseModel):
    fuerza: int
    destreza: int
    constitucion: int
    inteligencia: int
    sabiduria: int
    carisma: int


class PersonajeLLM(BaseModel):
    nombre: str
    descripcion_narrativa: str
    descripcion_visual_en: str
    inventario_inicial: list[str] = Field(default_factory=list)
    atributos: AtributosLLM


class WorldStateInicial(BaseModel):
    ubicacion_inicial: str
    objetivo: str


class PrimeraEscena(BaseModel):
    narrativa: str
    opciones: list[str]
    descripcion_imagen_en: str


class CreacionLLMResponse(BaseModel):
    personaje: PersonajeLLM
    world_state_inicial: WorldStateInicial
    primera_escena: PrimeraEscena
