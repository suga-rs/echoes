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
    ],
    "additionalProperties": False,
    "properties": {
        "narrativa": {"type": "string", "minLength": 50, "maxLength": 1500},
        "opciones": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {"type": "string", "minLength": 3, "maxLength": 100},
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
                "agregar_inventario": {"type": "array", "items": {"type": "string"}},
                "quitar_inventario": {"type": "array", "items": {"type": "string"}},
                "evento_clave": {"type": ["string", "null"]},
                "npc_encontrado": {
                    "oneOf": [
                        {"type": "null"},
                        {
                            "type": "object",
                            "required": ["nombre", "descripcion", "actitud"],
                            "additionalProperties": False,
                            "properties": {
                                "nombre": {"type": "string"},
                                "descripcion": {"type": "string", "maxLength": 200},
                                "actitud": {"enum": ["amistosa", "neutral", "hostil"]},
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
            "required": ["necesaria"],
            "additionalProperties": False,
            "properties": {
                "necesaria": {"type": "boolean"},
                "razon": {"type": "string"},
                "descripcion_escena_en": {"type": "string"},
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
            ],
            "additionalProperties": False,
            "properties": {
                "nombre": {"type": "string", "minLength": 1, "maxLength": 50},
                "descripcion_narrativa": {"type": "string", "maxLength": 300},
                "descripcion_visual_en": {"type": "string", "minLength": 50},
                "inventario_inicial": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 5,
                },
            },
        },
        "world_state_inicial": {
            "type": "object",
            "required": ["ubicacion_inicial", "objetivo"],
            "additionalProperties": False,
            "properties": {
                "ubicacion_inicial": {"type": "string"},
                "objetivo": {"type": "string"},
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
                    "items": {"type": "string"},
                },
                "descripcion_imagen_en": {"type": "string"},
            },
        },
    },
}


class GenerarImagen(BaseModel):
    necesaria: bool
    razon: str | None = None
    descripcion_escena_en: str | None = None


class NPCEncontrado(BaseModel):
    nombre: str
    descripcion: str
    actitud: str


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


class TurnoLLMResponse(BaseModel):
    narrativa: str
    opciones: list[str]
    actualizaciones_estado: ActualizacionesEstado
    generar_imagen: GenerarImagen
    estado_aventura: EstadoAventuraLLM


class PersonajeLLM(BaseModel):
    nombre: str
    descripcion_narrativa: str
    descripcion_visual_en: str
    inventario_inicial: list[str] = Field(default_factory=list)


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
