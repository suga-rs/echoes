"""Modelos de dominio."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Genero(str, Enum):
    FANTASIA = "fantasía"
    CIENCIA_FICCION = "ciencia ficción"
    TERROR = "terror"


class Actitud(str, Enum):
    AMISTOSA = "amistosa"
    NEUTRAL = "neutral"
    HOSTIL = "hostil"


class EstadoPartida(str, Enum):
    EN_CURSO = "en_curso"
    FINALIZADA = "finalizada"


class TipoFinal(str, Enum):
    EXITO = "exito"
    FRACASO = "fracaso"
    AMBIGUO = "ambiguo"


class Personaje(BaseModel):
    nombre: str
    descripcion_narrativa: str
    descripcion_visual_en: str
    inventario: list[str] = Field(default_factory=list)


class NPC(BaseModel):
    nombre: str
    descripcion: str
    actitud: Actitud


class WorldState(BaseModel):
    ubicacion_actual: str
    objetivo: str
    eventos_clave: list[str] = Field(default_factory=list)
    npcs: list[NPC] = Field(default_factory=list)
    pistas: list[str] = Field(default_factory=list)


class TurnoHistorial(BaseModel):
    turno: int
    accion_jugador: str
    narrativa: str
    opciones: list[str]
    imagen_url: str | None = None


class MetadataPartida(BaseModel):
    genero: Genero
    creada_en: datetime
    turno_actual: int = 0
    estado: EstadoPartida = EstadoPartida.EN_CURSO
    final: TipoFinal | None = None
    razon_fin: str | None = None
    imagenes_generadas: int = 0


class Partida(BaseModel):
    id: str
    codigo_partida: str
    metadata: MetadataPartida
    personaje: Personaje
    world_state: WorldState
    historial: list[TurnoHistorial] = Field(default_factory=list)


# DTOs


class StartPartidaRequest(BaseModel):
    genero: Genero
    descripcion_personaje: str = Field(..., min_length=10, max_length=300)


class TurnoRequest(BaseModel):
    accion: str = Field(..., min_length=1, max_length=200)


class TurnoResponse(BaseModel):
    turno: int
    narrativa: str
    opciones: list[str]
    imagen_url: str | None
    estado: EstadoPartida
    final: TipoFinal | None = None
    razon_fin: str | None = None


class StartResponse(BaseModel):
    codigo_partida: str
    personaje: Personaje
    objetivo: str
    primer_turno: TurnoResponse


class StateResponse(BaseModel):
    codigo_partida: str
    turno_actual: int
    estado: EstadoPartida
    personaje_nombre: str
    inventario: list[str]
    ubicacion: str
    objetivo: str
    eventos_clave: list[str]
    npcs_conocidos: list[str]


class ErrorResponse(BaseModel):
    code: str
    mensaje: str
    detalles: dict = Field(default_factory=dict)
