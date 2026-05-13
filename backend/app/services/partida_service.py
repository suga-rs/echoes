"""Servicio de partidas: orquesta LLM, imagen, persistencia."""

import asyncio
import json
import random
import secrets
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from jsonschema import ValidationError, validate

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    LimiteTurnosExcedido,
    PartidaFinalizada,
    RespuestaLLMInvalida,
)
from app.core.logging import get_logger
from app.models.domain import (
    NPC,
    Actitud,
    EstadoPartida,
    Genero,
    MetadataPartida,
    Partida,
    PartidaResumen,
    Personaje,
    StartResponse,
    TipoFinal,
    TurnoHistorial,
    TurnoResponse,
    WorldState,
)
from app.models.llm_schema import (
    CREACION_JSON_SCHEMA,
    TURNO_JSON_SCHEMA,
    CreacionLLMResponse,
    TurnoLLMResponse,
)
from app.repositories.imagen_repo import ImagenRepository
from app.repositories.partida_repo import PartidaRepository
from app.services.foundry_client import FoundryClient
from app.services.prompts import (
    SYSTEM_PROMPT_CREACION,
    SYSTEM_PROMPT_TURNO,
    build_creacion_user_prompt,
    build_image_prompt,
    build_retry_user_prompt,
    build_turno_user_prompt,
)

logger = get_logger("service.partidas")

_TIPOS_ACCION: dict[str, list[str]] = {
    "confrontacion": ["confrontar", "engañar", "intimidar"],
    "social": ["negociar", "ayudar_npc", "espiar"],
    "exploracion": ["inspeccionar", "buscar_ruta"],
    "recursos": ["usar_objeto", "improvisar"],
}


class PartidaService:
    def __init__(
        self,
        foundry: FoundryClient | None = None,
        partidas: PartidaRepository | None = None,
        imagenes: ImagenRepository | None = None,
        settings: Settings | None = None,
    ):
        self.settings = settings or get_settings()
        self.foundry = foundry or FoundryClient(self.settings)
        self.partidas = partidas or PartidaRepository(self.settings)
        self.imagenes = imagenes or ImagenRepository(self.settings)

    def crear_partida(self, genero: Genero, descripcion_personaje: str) -> StartResponse:
        logger.info("Creando partida: genero=%s", genero.value)

        system = SYSTEM_PROMPT_CREACION
        user = build_creacion_user_prompt(genero, descripcion_personaje)
        creacion = self._invocar_llm_con_reintento(
            system, user, CREACION_JSON_SCHEMA, CreacionLLMResponse
        )

        codigo = self._generar_codigo_partida()
        personaje = Personaje(
            nombre=creacion.personaje.nombre,
            descripcion_narrativa=creacion.personaje.descripcion_narrativa,
            descripcion_visual_en=creacion.personaje.descripcion_visual_en,
            inventario=list(creacion.personaje.inventario_inicial),
        )
        world_state = WorldState(
            ubicacion_actual=creacion.world_state_inicial.ubicacion_inicial,
            objetivo=creacion.world_state_inicial.objetivo,
        )
        metadata = MetadataPartida(
            genero=genero,
            creada_en=datetime.now(UTC),
            turno_actual=1,
            estado=EstadoPartida.EN_CURSO,
        )

        imagen_url = self._generar_imagen_segura(
            codigo_partida=codigo,
            turno=1,
            descripcion_visual_personaje_en=personaje.descripcion_visual_en,
            descripcion_escena_en=creacion.primera_escena.descripcion_imagen_en,
            genero=genero,
            imagenes_previas=0,
        )

        primer_turno = TurnoHistorial(
            turno=1,
            accion_jugador="<inicio>",
            narrativa=creacion.primera_escena.narrativa,
            opciones=list(creacion.primera_escena.opciones),
            imagen_url=imagen_url,
        )
        if imagen_url:
            metadata.imagenes_generadas = 1

        partida = Partida(
            id=codigo,
            codigo_partida=codigo,
            metadata=metadata,
            personaje=personaje,
            world_state=world_state,
            historial=[primer_turno],
        )
        self.partidas.upsert(partida)
        logger.info("Partida creada: codigo=%s", codigo)

        return StartResponse(
            codigo_partida=codigo,
            personaje=personaje,
            objetivo=world_state.objetivo,
            primer_turno=TurnoResponse(
                turno=1,
                narrativa=primer_turno.narrativa,
                opciones=primer_turno.opciones,
                imagen_url=imagen_url,
                estado=EstadoPartida.EN_CURSO,
            ),
        )

    def avanzar_turno(self, codigo_partida: str, accion: str) -> TurnoResponse:
        partida = self.partidas.get(codigo_partida)

        if partida.metadata.estado == EstadoPartida.FINALIZADA:
            raise PartidaFinalizada(
                f"La partida {codigo_partida} ya terminó",
                detalles={"final": partida.metadata.final},
            )

        if partida.metadata.turno_actual >= self.settings.max_turnos_por_partida:
            raise LimiteTurnosExcedido(
                f"La partida alcanzó el máximo de {self.settings.max_turnos_por_partida} turnos"
            )

        logger.info(
            "Avanzando turno: codigo=%s, turno_actual=%s",
            codigo_partida,
            partida.metadata.turno_actual,
        )

        system = SYSTEM_PROMPT_TURNO
        user = build_turno_user_prompt(partida, accion)
        turno_llm = self._invocar_llm_con_reintento(
            system, user, TURNO_JSON_SCHEMA, TurnoLLMResponse
        )

        nuevo_turno_num = partida.metadata.turno_actual + 1
        self._aplicar_actualizaciones(partida, turno_llm)

        imagen_url = None
        es_final = turno_llm.estado_aventura.tipo == "finalizada"
        if (
            turno_llm.generar_imagen.necesaria
            and turno_llm.generar_imagen.descripcion_escena_en
            and self._puede_generar_imagen(
                nuevo_turno_num, partida.metadata.imagenes_generadas, es_final
            )
        ):
            imagen_url = self._generar_imagen_segura(
                codigo_partida=codigo_partida,
                turno=nuevo_turno_num,
                descripcion_visual_personaje_en=partida.personaje.descripcion_visual_en,
                descripcion_escena_en=turno_llm.generar_imagen.descripcion_escena_en,
                genero=partida.metadata.genero,
                imagenes_previas=partida.metadata.imagenes_generadas,
            )
            if imagen_url:
                partida.metadata.imagenes_generadas += 1

        nuevo_turno = TurnoHistorial(
            turno=nuevo_turno_num,
            accion_jugador=accion,
            narrativa=turno_llm.narrativa,
            opciones=list(turno_llm.opciones),
            imagen_url=imagen_url,
        )
        partida.historial.append(nuevo_turno)
        partida.metadata.turno_actual = nuevo_turno_num

        if turno_llm.estado_aventura.tipo == "finalizada":
            partida.metadata.estado = EstadoPartida.FINALIZADA
            if turno_llm.estado_aventura.final:
                try:
                    partida.metadata.final = TipoFinal(turno_llm.estado_aventura.final)
                except ValueError:
                    pass
            partida.metadata.razon_fin = turno_llm.estado_aventura.razon_fin

        self.partidas.upsert(partida)

        return TurnoResponse(
            turno=nuevo_turno_num,
            narrativa=turno_llm.narrativa,
            opciones=list(turno_llm.opciones),
            imagen_url=imagen_url,
            estado=partida.metadata.estado,
            final=partida.metadata.final,
            razon_fin=partida.metadata.razon_fin,
        )

    def get_partida(self, codigo_partida: str) -> Partida:
        return self.partidas.get(codigo_partida)

    def listar_partidas(self) -> list[PartidaResumen]:
        return self.partidas.list_all()

    def generar_descripcion_aleatoria(self, genero: Genero) -> str:
        system = (
            "Eres un asistente creativo para juegos de aventura de texto. "
            'Responde siempre con JSON: {"descripcion": "<texto>"}'
        )
        user = (
            f"Genera una descripción creativa de personaje para una aventura de {genero.value}. "
            "Máximo 280 caracteres. Solo la descripción, sin nombre ni comillas."
        )
        _, parsed = self.foundry.chat_json_raw(system, user)
        descripcion = parsed.get("descripcion") if parsed is not None else None
        if not descripcion or not isinstance(descripcion, str):
            raise RespuestaLLMInvalida(
                "LLM no devolvió el campo 'descripcion' esperado",
                detalles={"respuesta": str(parsed)[:200]},
            )
        return descripcion[:280]

    def _invocar_llm_con_reintento(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict,
        modelo_pydantic: type,
    ):
        system_with_schema = (
            f"{system_prompt}\n\n# SCHEMA JSON ESPERADO\n{json.dumps(json_schema, indent=2)}"
        )

        raw, parsed = self.foundry.chat_json_raw(system_with_schema, user_prompt)

        if parsed is not None:
            try:
                validate(parsed, json_schema)
                return modelo_pydantic.model_validate(parsed)
            except ValidationError as e:
                error_msg = self._summarize_validation_error(e)
                logger.warning("Schema inválido en intento 1: %s", error_msg)
        else:
            error_msg = "respuesta no es JSON parseable"
            logger.warning("JSON inválido en intento 1")

        retry_user = build_retry_user_prompt(raw, error_msg)
        raw2, parsed2 = self.foundry.chat_json_raw(system_prompt, retry_user)

        if parsed2 is None:
            raise RespuestaLLMInvalida(
                "LLM devolvió JSON inválido en dos intentos",
                detalles={"ultimo_intento": raw2[:500]},
            )

        try:
            validate(parsed2, json_schema)
        except ValidationError as e:
            error_msg = self._summarize_validation_error(e)
            raise RespuestaLLMInvalida(
                f"LLM no respetó el schema tras reintento: {error_msg}",
                detalles={"ultimo_intento": raw2[:500]},
            ) from e

        return modelo_pydantic.model_validate(parsed2)

    @staticmethod
    def _summarize_validation_error(err: ValidationError) -> str:
        path = ".".join(str(p) for p in err.absolute_path) or "(root)"
        return f"{path}: {err.message}"

    def _aplicar_actualizaciones(self, partida: Partida, turno_llm: TurnoLLMResponse) -> None:
        upd = turno_llm.actualizaciones_estado
        ws = partida.world_state
        pj = partida.personaje

        if upd.ubicacion_nueva:
            ws.ubicacion_actual = upd.ubicacion_nueva

        for item in upd.agregar_inventario:
            if item not in pj.inventario:
                pj.inventario.append(item)

        for item in upd.quitar_inventario:
            if item in pj.inventario:
                pj.inventario.remove(item)

        if upd.evento_clave:
            ws.eventos_clave.append(upd.evento_clave)

        if upd.npc_encontrado:
            if not any(n.nombre == upd.npc_encontrado.nombre for n in ws.npcs):
                try:
                    actitud = Actitud(upd.npc_encontrado.actitud)
                except ValueError:
                    actitud = Actitud.NEUTRAL
                ws.npcs.append(
                    NPC(
                        nombre=upd.npc_encontrado.nombre,
                        descripcion=upd.npc_encontrado.descripcion,
                        actitud=actitud,
                    )
                )

        if upd.npc_actitud_cambio:
            for npc in ws.npcs:
                if npc.nombre == upd.npc_actitud_cambio.nombre:
                    try:
                        npc.actitud = Actitud(upd.npc_actitud_cambio.nueva_actitud)
                    except ValueError:
                        pass
                    break

        if upd.pista_descubierta:
            ws.pistas.append(upd.pista_descubierta)

    def _generar_imagen_segura(
        self,
        *,
        codigo_partida: str,
        turno: int,
        descripcion_visual_personaje_en: str,
        descripcion_escena_en: str,
        genero: Genero,
        imagenes_previas: int,
    ) -> str | None:
        if imagenes_previas >= self.settings.max_imagenes_por_partida:
            logger.info("Límite de imágenes alcanzado")
            return None

        try:
            prompt = build_image_prompt(
                descripcion_visual_personaje_en, descripcion_escena_en, genero
            )
            png = self.foundry.generar_imagen(prompt)
            return self.imagenes.subir_imagen(codigo_partida, turno, png)
        except Exception:
            logger.exception("Falló generación de imagen para %s", codigo_partida)
            return None

    def _puede_generar_imagen(
        self, turno_actual: int, imagenes_generadas: int, es_final: bool
    ) -> bool:
        max_img = self.settings.max_imagenes_por_partida
        max_t = self.settings.max_turnos_por_partida
        slots_regulares = max_img - 1
        intervalo = max_t / max_img

        if es_final:
            return imagenes_generadas < max_img

        if imagenes_generadas >= slots_regulares:
            return False

        return turno_actual >= (imagenes_generadas + 1) * intervalo

    async def avanzar_turno_stream(
        self, codigo_partida: str, accion: str
    ) -> AsyncGenerator[str, None]:
        """SSE stream: yields token/turno/imagen/done events."""

        def _sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        partida = await asyncio.to_thread(self.partidas.get, codigo_partida)

        if partida.metadata.estado == EstadoPartida.FINALIZADA:
            raise PartidaFinalizada(
                f"La partida {codigo_partida} ya terminó",
                detalles={"final": partida.metadata.final},
            )
        if partida.metadata.turno_actual >= self.settings.max_turnos_por_partida:
            raise LimiteTurnosExcedido(
                f"La partida alcanzó el máximo de {self.settings.max_turnos_por_partida} turnos"
            )

        logger.info(
            "Avanzando turno (stream): codigo=%s, turno_actual=%s",
            codigo_partida,
            partida.metadata.turno_actual,
        )

        system_with_schema = (
            f"{SYSTEM_PROMPT_TURNO}\n\n# SCHEMA JSON ESPERADO\n"
            f"{json.dumps(TURNO_JSON_SCHEMA, indent=2)}"
        )
        user = build_turno_user_prompt(partida, accion)

        extractor = _NarrativaExtractor()
        accumulated = ""

        async for chunk in self.foundry.chat_streaming_async(system_with_schema, user):
            accumulated += chunk
            text = extractor.feed(chunk)
            if text:
                yield _sse("token", {"content": text})

        # Parse completed JSON
        try:
            parsed = json.loads(accumulated)
        except json.JSONDecodeError:
            raise RespuestaLLMInvalida(
                "Stream LLM devolvió JSON inválido",
                detalles={"inicio": accumulated[:200]},
            )

        try:
            validate(parsed, TURNO_JSON_SCHEMA)
        except ValidationError as e:
            raise RespuestaLLMInvalida(
                f"JSON del stream no respeta el schema: {self._summarize_validation_error(e)}",
                detalles={"inicio": accumulated[:200]},
            )

        turno_llm = TurnoLLMResponse.model_validate(parsed)

        nuevo_turno_num = partida.metadata.turno_actual + 1
        es_final = turno_llm.estado_aventura.tipo == "finalizada"
        self._aplicar_actualizaciones(partida, turno_llm)

        # Persist turn (without image URL yet)
        nuevo_turno = TurnoHistorial(
            turno=nuevo_turno_num,
            accion_jugador=accion,
            narrativa=turno_llm.narrativa,
            opciones=list(turno_llm.opciones),
            imagen_url=None,
        )
        partida.historial.append(nuevo_turno)
        partida.metadata.turno_actual = nuevo_turno_num

        if es_final:
            partida.metadata.estado = EstadoPartida.FINALIZADA
            if turno_llm.estado_aventura.final:
                try:
                    partida.metadata.final = TipoFinal(turno_llm.estado_aventura.final)
                except ValueError:
                    pass
            partida.metadata.razon_fin = turno_llm.estado_aventura.razon_fin

        await asyncio.to_thread(self.partidas.upsert, partida)

        imagen_solicitada = (
            turno_llm.generar_imagen.necesaria
            and bool(turno_llm.generar_imagen.descripcion_escena_en)
            and self._puede_generar_imagen(
                nuevo_turno_num, partida.metadata.imagenes_generadas, es_final
            )
        )

        yield _sse(
            "turno",
            {
                "turno": nuevo_turno_num,
                "narrativa": turno_llm.narrativa,
                "opciones": list(turno_llm.opciones),
                "estado": partida.metadata.estado.value,
                "final": partida.metadata.final.value if partida.metadata.final else None,
                "razon_fin": partida.metadata.razon_fin,
                "imagen_pendiente": imagen_solicitada,
            },
        )

        # Generate image asynchronously (SSE connection stays open)
        if imagen_solicitada:
            imagen_url = await asyncio.to_thread(
                self._generar_imagen_segura,
                codigo_partida=codigo_partida,
                turno=nuevo_turno_num,
                descripcion_visual_personaje_en=partida.personaje.descripcion_visual_en,
                descripcion_escena_en=turno_llm.generar_imagen.descripcion_escena_en,
                genero=partida.metadata.genero,
                imagenes_previas=partida.metadata.imagenes_generadas,
            )
            if imagen_url:
                partida.metadata.imagenes_generadas += 1
                partida.historial[-1].imagen_url = imagen_url
                await asyncio.to_thread(self.partidas.upsert, partida)
                yield _sse("imagen", {"imagen_url": imagen_url})

        yield _sse("done", {})

    @staticmethod
    def _generar_codigo_partida() -> str:
        alphabet = "abcdefghijkmnpqrstuvwxyz23456789"
        groups = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3)]
        return "-".join(groups)

    def _seleccionar_tipos_accion(self, partida: Partida) -> list[str]:
        rng = random.Random(partida.metadata.turno_actual)

        prioritarias = []
        if partida.world_state.npcs:
            prioritarias.append("social")
        if partida.personaje.inventario:
            prioritarias.append("recursos")

        restantes = [c for c in _TIPOS_ACCION if c not in prioritarias]
        rng.shuffle(restantes)

        seleccionadas = (prioritarias + restantes)[:3]
        rng.shuffle(seleccionadas)

        return [rng.choice(_TIPOS_ACCION[cat]) for cat in seleccionadas]


class _NarrativaExtractor:
    """Extracts the 'narrativa' string value from streaming JSON tokens."""

    def __init__(self) -> None:
        self._buf = ""
        self._state = "searching"  # searching | in_value | done
        self._escape = False

    def feed(self, chunk: str) -> str:
        result: list[str] = []
        for ch in chunk:
            if self._state == "done":
                break
            if self._state == "searching":
                self._buf += ch
                marker = '"narrativa": "'
                if marker in self._buf:
                    after = self._buf[self._buf.index(marker) + len(marker) :]
                    self._buf = ""
                    self._state = "in_value"
                    result.extend(self._consume(after))
            elif self._state == "in_value":
                result.extend(self._consume(ch))
        return "".join(result)

    def _consume(self, text: str) -> list[str]:
        chars: list[str] = []
        for ch in text:
            if self._state != "in_value":
                break
            if self._escape:
                mapping = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}
                chars.append(mapping.get(ch, ch))
                self._escape = False
            elif ch == "\\":
                self._escape = True
            elif ch == '"':
                self._state = "done"
            else:
                chars.append(ch)
        return chars
