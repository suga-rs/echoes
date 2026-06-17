"""Modelos de dominio."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class Genero(StrEnum):
    FANTASIA = "fantasía"
    CIENCIA_FICCION = "ciencia ficción"
    TERROR = "terror"


class Actitud(StrEnum):
    AMISTOSA = "amistosa"
    NEUTRAL = "neutral"
    HOSTIL = "hostil"


class EstadoPartida(StrEnum):
    EN_CURSO = "en_curso"
    FINALIZADA = "finalizada"


class TipoFinal(StrEnum):
    EXITO = "exito"
    FRACASO = "fracaso"
    AMBIGUO = "ambiguo"


class FaseNarrativa(StrEnum):
    INTRODUCCION = "introduccion"
    DESARROLLO = "desarrollo"
    CLIMAX = "climax"
    RESOLUCION = "resolucion"


class Personaje(BaseModel):
    nombre: str
    descripcion_narrativa: str
    descripcion_visual_en: str
    inventario: list[str] = Field(default_factory=list)
    # URL de la imagen de referencia canónica del personaje (retrato de cuerpo
    # entero, fondo neutro). Se genera una sola vez por partida y se reutiliza
    # como ancla visual en cada imagen de escena vía images.edit. None hasta que
    # se genera la primera imagen; partidas previas deserializan como None.
    referencia_visual_url: str | None = None


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
    # Arco narrativo: reemplaza al conteo de turnos como reloj dramático.
    # Partidas previas a este cambio (Cosmos schemaless) deserializan con
    # estos defaults seguros.
    fase_narrativa: FaseNarrativa = FaseNarrativa.INTRODUCCION
    tension: int = 1
    # Resumen acumulado de la historia que el narrador reescribe cada turno;
    # mantiene la coherencia en partidas largas sin reinyectar todo el historial.
    resumen_historia: str = ""


class TurnoHistorial(BaseModel):
    turno: int
    accion_jugador: str
    narrativa: str
    opciones: list[str]
    imagen_url: str | None = None
    descripcion_escena_en: str | None = None
    feedback: str | None = None  # señal de calidad del jugador: "incoherente" | "ok"


class MetadataPartida(BaseModel):
    genero: Genero
    creada_en: datetime
    actualizada_en: datetime | None = None
    turno_actual: int = 0
    # Dueño de la partida. Las partidas anónimas y las previas a la introducción
    # de cuentas pertenecen al usuario "Creator" (user_id == "0").
    user_id: str = "0"
    estado: EstadoPartida = EstadoPartida.EN_CURSO
    final: TipoFinal | None = None
    razon_fin: str | None = None
    imagenes_generadas: int = 0
    # Versión de prompts/contrato con la que se creó la partida (auditoría).
    # Las partidas previas sin el campo deserializan como None (Cosmos schemaless).
    prompt_version: str | None = None
    # Gate de "solo partidas nuevas" para el flujo de referencia visual del
    # personaje. Lo activa crear_partida; las partidas previas deserializan como
    # False y siguen en el flujo de imagen por texto (images.generate).
    usa_referencia_visual: bool = False


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
    # Inputs creativos opcionales del jugador. Si se dan, el narrador los honra;
    # si no, los cubre la semilla muestreada server-side.
    premisa: str | None = Field(default=None, max_length=200)
    tono: str | None = Field(default=None, max_length=100)


class TurnoRequest(BaseModel):
    accion: str = Field(..., min_length=1, max_length=200)


class FeedbackRequest(BaseModel):
    incoherente: bool


class FeedbackResponse(BaseModel):
    feedback: str | None


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


class ImagenTurnoResponse(BaseModel):
    imagen_url: str


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


class PartidaResumen(BaseModel):
    codigo_partida: str
    nombre_personaje: str
    turno_actual: int
    estado: EstadoPartida
    genero: Genero
    creada_en: datetime
    actualizada_en: datetime | None = None
    # Versión del contrato de prompts con que se creó. Las partidas previas sin
    # el campo (Cosmos schemaless) se presentan como la versión inicial.
    prompt_version: str = "1.0.0"

    @field_validator("prompt_version", mode="before")
    @classmethod
    def _normalizar_prompt_version(cls, v: str | None) -> str:
        return v or "1.0.0"


class RandomDescriptionRequest(BaseModel):
    genero: Genero


class RandomDescriptionResponse(BaseModel):
    descripcion: str


# Usuarios / Autenticación


class Usuario(BaseModel):
    """Documento de usuario persistido en Cosmos (container `usuarios`)."""

    id: str
    username: str
    username_lower: str
    password_hash: str
    creada_en: datetime
    avatar_url: str | None = None


class UsuarioPublico(BaseModel):
    """Vista pública del usuario: nunca expone el hash de la contraseña."""

    id: str
    username: str
    creada_en: datetime
    avatar_url: str | None = None


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    # bcrypt opera sobre los primeros 72 bytes; limitamos arriba para evitar
    # sorpresas de truncado silencioso.
    password: str = Field(..., min_length=8, max_length=72)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=32)
    password: str = Field(..., min_length=1, max_length=72)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UsuarioPublico


class PerfilResponse(BaseModel):
    user: UsuarioPublico
    partidas: list[PartidaResumen] = Field(default_factory=list)


class AvatarResponse(BaseModel):
    avatar_url: str
