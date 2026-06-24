"""Modelos de dominio."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


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


class Habilidad(StrEnum):
    """Las seis habilidades clásicas de D&D que puede nombrar una tirada."""

    FUERZA = "fuerza"
    DESTREZA = "destreza"
    CONSTITUCION = "constitucion"
    INTELIGENCIA = "inteligencia"
    SABIDURIA = "sabiduria"
    CARISMA = "carisma"


class Banda(StrEnum):
    """Banda de dificultad declarada por el narrador. El sistema mapea cada
    banda a un DC fijo (ver app.services.dados); el narrador nunca da un número."""

    TRIVIAL = "trivial"
    FACIL = "facil"
    MEDIA = "media"
    DIFICIL = "dificil"
    HEROICA = "heroica"


class ResultadoTirada(StrEnum):
    EXITO_CRITICO = "exito_critico"
    EXITO = "exito"
    FRACASO = "fracaso"
    FRACASO_CRITICO = "fracaso_critico"


class BandaSeveridad(StrEnum):
    """Banda de severidad de daño declarada por el narrador. El sistema mapea
    cada banda a una FRACCIÓN de pv_max (ver app.services.vida); el narrador
    nunca da un número de PV, igual que nunca da un DC en las tiradas."""

    RASGUNO = "rasguno"
    LEVE = "leve"
    GRAVE = "grave"
    SEVERO = "severo"
    MORTAL = "mortal"


class TipoCondicion(StrEnum):
    ENVENENADO = "envenenado"
    SANGRANDO = "sangrando"
    ATURDIDO = "aturdido"
    EXHAUSTO = "exhausto"


class EfectoCondicion(StrEnum):
    """Efectos mecánicos soportados en este hito. `desventaja` hace que la
    resolución del d20 tire dos dados y se quede con el peor; `dano_por_turno`
    descuenta PV al comienzo de cada turno mientras la condición esté activa."""

    DESVENTAJA = "desventaja"
    DANO_POR_TURNO = "dano_por_turno"


class DuracionCondicion(StrEnum):
    """Duraciones no numéricas. Una duración numérica (int de turnos) se
    decrementa cada turno; estas persisten hasta que un evento las quite."""

    HASTA_CURAR = "hasta_curar"
    HASTA_EVENTO = "hasta_evento"


class Condicion(BaseModel):
    """Condición activa sobre el personaje: un tipo, su efecto mecánico y su
    duración (int de turnos, o un sentinel no numérico)."""

    tipo: TipoCondicion
    efecto: EfectoCondicion
    # int = cantidad de turnos restantes; DuracionCondicion = hasta evento/cura.
    duracion: int | DuracionCondicion


class Atributos(BaseModel):
    """Las seis habilidades clásicas (3-18). El modificador es el estándar de
    D&D: floor((score-10)/2). Las partidas previas a este cambio (sin el bloque)
    deserializan con los seis en 10 (+0) vía el default en Personaje."""

    fuerza: int = Field(ge=3, le=18)
    destreza: int = Field(ge=3, le=18)
    constitucion: int = Field(ge=3, le=18)
    inteligencia: int = Field(ge=3, le=18)
    sabiduria: int = Field(ge=3, le=18)
    carisma: int = Field(ge=3, le=18)

    def modificador(self, habilidad: "Habilidad") -> int:
        import math

        return math.floor((getattr(self, habilidad.value) - 10) / 2)

    @classmethod
    def neutral(cls) -> "Atributos":
        return cls(
            fuerza=10, destreza=10, constitucion=10, inteligencia=10, sabiduria=10, carisma=10
        )


class Tirada(BaseModel):
    """Registro de una tirada resuelta, persistido en el turno. El d20 es la
    fuente de verdad (tirado server-side); la animación solo lo muestra."""

    habilidad: Habilidad
    banda: Banda
    dc: int
    d20: int
    modificador: int
    total: int
    resultado: ResultadoTirada


class Personaje(BaseModel):
    nombre: str
    descripcion_narrativa: str
    descripcion_visual_en: str
    inventario: list[str] = Field(default_factory=list)
    # Ficha de seis atributos. Las partidas previas a este cambio (Cosmos
    # schemaless) deserializan con los seis en 10 (+0) y siguen jugables.
    atributos: Atributos = Field(default_factory=Atributos.neutral)
    # Puntos de vida. pv_max se deriva de la constitución (ver app.services.vida);
    # un valor 0 o ausente (partidas previas a este cambio) se rellena en
    # _derivar_pv: pv_max desde la constitución y pv_actual a tope. El sistema es
    # dueño de estos números; el narrador nunca emite PV crudos.
    pv_max: int = 0
    pv_actual: int = 0
    # Condiciones activas (envenenado, sangrando, ...). Partidas previas
    # deserializan con la lista vacía.
    condiciones: list[Condicion] = Field(default_factory=list)
    # URL de la imagen de referencia canónica del personaje (retrato de cuerpo
    # entero, fondo neutro). Se genera una sola vez por partida y se reutiliza
    # como ancla visual en cada imagen de escena vía images.edit. None hasta que
    # se genera la primera imagen; partidas previas deserializan como None.
    referencia_visual_url: str | None = None

    @model_validator(mode="after")
    def _derivar_pv(self) -> "Personaje":
        # Retrocompat: documentos sin PV (o con 0) derivan pv_max de la
        # constitución y arrancan a tope. Un pv_actual ya persistido (> 0) se
        # respeta. Import diferido para no acoplar el dominio a services.vida.
        from app.services.vida import pv_max_de_constitucion

        if self.pv_max <= 0:
            self.pv_max = pv_max_de_constitucion(self.atributos.constitucion)
        if self.pv_actual <= 0:
            self.pv_actual = self.pv_max
        return self


class NPC(BaseModel):
    nombre: str
    descripcion: str
    actitud: Actitud
    # Descripción visual canónica en inglés, capturada al introducir el NPC y
    # reutilizada como ancla de texto en cada imagen donde aparece (mantiene su
    # apariencia consistente entre imágenes). None en NPCs de partidas previas a
    # este cambio (Cosmos schemaless), tratados como "sin ancla".
    descripcion_visual_en: str | None = None


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
    # Nombres de NPCs presentes en la escena de este turno, para anclar su
    # apariencia al generar la imagen (incluida la generación a demanda posterior).
    # Lista vacía en turnos previos a este cambio (Cosmos schemaless).
    npcs_en_escena: list[str] = Field(default_factory=list)
    feedback: str | None = None  # señal de calidad del jugador: "incoherente" | "ok"
    # Tirada resuelta en este turno, o None si la acción no requirió un check.
    # Los turnos previos a este cambio (Cosmos schemaless) deserializan como None.
    tirada: Tirada | None = None


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
    # Tirada resuelta en este turno, o None si la acción no requirió un check.
    tirada: Tirada | None = None
    # Estado de vida tras este turno y daño recibido en él (tick + golpe). Las
    # partidas previas a este cambio igual reportan pv_max/pv_actual vía el
    # default derivado en Personaje.
    pv_actual: int = 0
    pv_max: int = 0
    condiciones: list[Condicion] = Field(default_factory=list)
    dano_recibido: int = 0


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
    pv_actual: int = 0
    pv_max: int = 0
    condiciones: list[Condicion] = Field(default_factory=list)


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
