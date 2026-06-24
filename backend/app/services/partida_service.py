"""Servicio de partidas: orquesta LLM, imagen, persistencia."""

import asyncio
import contextlib
import json
import random
import secrets
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import TypeVar

from jsonschema import ValidationError, validate
from pydantic import BaseModel

from app.core import telemetry
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AccesoDenegadoError,
    FoundryError,
    LimiteImagenesExcedidoError,
    PartidaFinalizadaError,
    PartidaNoEncontradaError,
    RespuestaLLMInvalidaError,
)
from app.core.logging import get_logger
from app.models.domain import (
    NPC,
    Actitud,
    Atributos,
    Banda,
    EstadoPartida,
    FaseNarrativa,
    Genero,
    Habilidad,
    MetadataPartida,
    Partida,
    PartidaResumen,
    Personaje,
    StartResponse,
    TipoFinal,
    Tirada,
    TurnoHistorial,
    TurnoResponse,
    WorldState,
)
from app.models.llm_schema import (
    CREACION_JSON_SCHEMA,
    TURNO_JSON_SCHEMA,
    CreacionLLMResponse,
    RequiereTirada,
    TurnoLLMResponse,
)
from app.repositories.imagen_repo import ImagenRepository
from app.repositories.partida_repo import PartidaRepository
from app.services import dados
from app.services.foundry_client import FoundryClient
from app.services.prompts import (
    PROMPT_VERSION,
    SYSTEM_PROMPT_CREACION,
    SYSTEM_PROMPT_RESOLUCION,
    SYSTEM_PROMPT_TURNO,
    build_creacion_user_prompt,
    build_image_prompt,
    build_reference_prompt,
    build_resolucion_user_prompt,
    build_retry_user_prompt,
    build_turno_user_prompt,
    sample_seed,
)

logger = get_logger("service.partidas")

_PydanticT = TypeVar("_PydanticT", bound=BaseModel)


class PartidaService:
    def __init__(
        self,
        foundry: FoundryClient | None = None,
        partidas: PartidaRepository | None = None,
        imagenes: ImagenRepository | None = None,
        settings: Settings | None = None,
        rng: random.Random | None = None,
    ):
        self.settings = settings or get_settings()
        self.foundry = foundry or FoundryClient(self.settings)
        self.partidas = partidas or PartidaRepository(self.settings)
        self.imagenes = imagenes or ImagenRepository(self.settings)
        # Fuente de azar de los dados. Inyectable para tests deterministas; en
        # producción una fuente fresca por servicio.
        self._rng = rng or random.Random()

    @telemetry.traced("crear_partida")
    def crear_partida(
        self,
        genero: Genero,
        descripcion_personaje: str,
        owner_id: str = "0",
        premisa: str | None = None,
        tono: str | None = None,
    ) -> StartResponse:
        telemetry.add_span_attributes(genero=genero.value, prompt_version=PROMPT_VERSION)
        logger.info("Creando partida: genero=%s, prompt_version=%s", genero.value, PROMPT_VERSION)

        system = SYSTEM_PROMPT_CREACION
        seed = sample_seed(genero)
        user = build_creacion_user_prompt(
            genero, descripcion_personaje, seed, premisa=premisa, tono=tono
        )
        creacion = self._invocar_llm_con_reintento(
            system, user, CREACION_JSON_SCHEMA, CreacionLLMResponse
        )

        codigo = self._generar_codigo_partida()
        personaje = Personaje(
            nombre=creacion.personaje.nombre,
            descripcion_narrativa=creacion.personaje.descripcion_narrativa,
            descripcion_visual_en=creacion.personaje.descripcion_visual_en,
            inventario=list(creacion.personaje.inventario_inicial),
            atributos=Atributos(
                fuerza=creacion.personaje.atributos.fuerza,
                destreza=creacion.personaje.atributos.destreza,
                constitucion=creacion.personaje.atributos.constitucion,
                inteligencia=creacion.personaje.atributos.inteligencia,
                sabiduria=creacion.personaje.atributos.sabiduria,
                carisma=creacion.personaje.atributos.carisma,
            ),
        )
        world_state = WorldState(
            ubicacion_actual=creacion.world_state_inicial.ubicacion_inicial,
            objetivo=creacion.world_state_inicial.objetivo,
        )
        metadata = MetadataPartida(
            genero=genero,
            creada_en=datetime.now(UTC),
            actualizada_en=datetime.now(UTC),
            turno_actual=1,
            estado=EstadoPartida.EN_CURSO,
            prompt_version=PROMPT_VERSION,
            user_id=owner_id,
            # Las partidas nuevas anclan sus imágenes a la referencia del personaje.
            usa_referencia_visual=True,
        )

        imagen_url = self._generar_imagen_segura(
            codigo_partida=codigo,
            turno=1,
            personaje=personaje,
            descripcion_escena_en=creacion.primera_escena.descripcion_imagen_en,
            genero=genero,
            imagenes_previas=0,
            usa_referencia=metadata.usa_referencia_visual,
        )

        primer_turno = TurnoHistorial(
            turno=1,
            accion_jugador="<inicio>",
            narrativa=creacion.primera_escena.narrativa,
            opciones=list(creacion.primera_escena.opciones),
            imagen_url=imagen_url,
            descripcion_escena_en=creacion.primera_escena.descripcion_imagen_en,
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

    @telemetry.traced("avanzar_turno")
    def avanzar_turno(self, codigo_partida: str, accion: str) -> TurnoResponse:
        partida = self.partidas.get(codigo_partida)
        telemetry.add_span_attributes(
            codigo_partida=codigo_partida,
            turno=partida.metadata.turno_actual,
            genero=partida.metadata.genero.value,
            prompt_version=PROMPT_VERSION,
        )

        if partida.metadata.estado == EstadoPartida.FINALIZADA:
            raise PartidaFinalizadaError(
                f"La partida {codigo_partida} ya terminó",
                detalles={"final": partida.metadata.final},
            )

        logger.info(
            "Avanzando turno: codigo=%s, turno_actual=%s, prompt_version=%s",
            codigo_partida,
            partida.metadata.turno_actual,
            PROMPT_VERSION,
        )

        system = SYSTEM_PROMPT_TURNO
        user = build_turno_user_prompt(partida, accion)
        turno_llm = self._invocar_llm_con_reintento(
            system, user, TURNO_JSON_SCHEMA, TurnoLLMResponse
        )

        # Fase 2: si el narrador declaró una tirada, tiramos un d20 real y le
        # pedimos que narre el desenlace honrando el resultado. La narración de
        # la fase 1 (la preparación) se descarta; la fase 2 es el turno autoritativo.
        tirada = None
        if turno_llm.requiere_tirada is not None:
            tirada = self._resolver_tirada(partida, turno_llm.requiere_tirada)
            user2 = build_resolucion_user_prompt(partida, accion, tirada)
            turno_llm = self._invocar_llm_con_reintento(
                SYSTEM_PROMPT_RESOLUCION, user2, TURNO_JSON_SCHEMA, TurnoLLMResponse
            )

        nuevo_turno_num = partida.metadata.turno_actual + 1
        self._aplicar_actualizaciones(partida, turno_llm)

        # La imagen del primer y último turno se genera automáticamente; el resto
        # las pide el jugador a demanda vía generar_imagen_turno.
        imagen_url = None
        es_final = turno_llm.estado_aventura.tipo == "finalizada"
        descripcion_escena = turno_llm.generar_imagen.descripcion_escena_en
        if es_final and descripcion_escena:
            imagen_url = self._generar_imagen_segura(
                codigo_partida=codigo_partida,
                turno=nuevo_turno_num,
                personaje=partida.personaje,
                descripcion_escena_en=descripcion_escena,
                genero=partida.metadata.genero,
                imagenes_previas=partida.metadata.imagenes_generadas,
                usa_referencia=partida.metadata.usa_referencia_visual,
            )
            if imagen_url:
                partida.metadata.imagenes_generadas += 1

        nuevo_turno = TurnoHistorial(
            turno=nuevo_turno_num,
            accion_jugador=accion,
            narrativa=turno_llm.narrativa,
            opciones=list(turno_llm.opciones),
            imagen_url=imagen_url,
            descripcion_escena_en=descripcion_escena,
            tirada=tirada,
        )
        partida.historial.append(nuevo_turno)
        partida.metadata.turno_actual = nuevo_turno_num
        partida.metadata.actualizada_en = datetime.now(UTC)

        if turno_llm.estado_aventura.tipo == "finalizada":
            partida.metadata.estado = EstadoPartida.FINALIZADA
            if turno_llm.estado_aventura.final:
                with contextlib.suppress(ValueError):
                    partida.metadata.final = TipoFinal(turno_llm.estado_aventura.final)
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
            tirada=tirada,
        )

    def get_partida(self, codigo_partida: str) -> Partida:
        return self.partidas.get(codigo_partida)

    def registrar_feedback(self, codigo_partida: str, turno: int, incoherente: bool) -> str:
        """Marca un turno con feedback de calidad del jugador y lo persiste."""
        partida = self.partidas.get(codigo_partida)
        turno_obj = next((t for t in partida.historial if t.turno == turno), None)
        if turno_obj is None:
            raise PartidaNoEncontradaError(
                f"Turno {turno} no encontrado en la partida {codigo_partida}"
            )

        turno_obj.feedback = "incoherente" if incoherente else "ok"
        self.partidas.upsert(partida)
        telemetry.record_feedback(incoherente=incoherente)
        logger.info(
            "Feedback de turno: codigo=%s, turno=%s, incoherente=%s",
            codigo_partida,
            turno,
            incoherente,
        )
        return turno_obj.feedback

    def listar_partidas(self, user_id: str | None = None) -> list[PartidaResumen]:
        return self.partidas.list_all(user_id=user_id)

    @telemetry.traced("eliminar_partida")
    def eliminar_partida(self, codigo_partida: str, user_id: str) -> None:
        """Elimina una partida del usuario que la posee. Rechaza el bucket
        compartido del Creator ("0") y a quien no sea el dueño. Limpia los blobs
        de imagen (best-effort) antes de borrar el documento, que es el resultado
        autoritativo de la operación."""
        partida = self.partidas.get(codigo_partida)  # 404 si no existe
        owner = partida.metadata.user_id
        if owner == "0":
            raise AccesoDenegadoError("Las partidas del Creator no se pueden eliminar")
        if owner != user_id:
            raise AccesoDenegadoError("No podés eliminar una partida que no es tuya")

        try:
            self.imagenes.eliminar_imagenes(codigo_partida)
        except Exception:
            logger.exception("Falló la limpieza de imágenes de %s", codigo_partida)

        self.partidas.delete(codigo_partida)
        logger.info("Partida eliminada: codigo=%s, user_id=%s", codigo_partida, user_id)

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
            raise RespuestaLLMInvalidaError(
                "LLM no devolvió el campo 'descripcion' esperado",
                detalles={"respuesta": str(parsed)[:200]},
            )
        return descripcion[:280]

    def _invocar_llm_con_reintento(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict,
        modelo_pydantic: type[_PydanticT],
    ) -> _PydanticT:
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
            telemetry.record_llm_error(operation="invocar", tipo="json")
            raise RespuestaLLMInvalidaError(
                "LLM devolvió JSON inválido en dos intentos",
                detalles={"ultimo_intento": raw2[:500]},
            )

        try:
            validate(parsed2, json_schema)
        except ValidationError as e:
            error_msg = self._summarize_validation_error(e)
            telemetry.record_llm_error(operation="invocar", tipo="schema")
            raise RespuestaLLMInvalidaError(
                f"LLM no respetó el schema tras reintento: {error_msg}",
                detalles={"ultimo_intento": raw2[:500]},
            ) from e

        return modelo_pydantic.model_validate(parsed2)

    @staticmethod
    def _summarize_validation_error(err: ValidationError) -> str:
        path = ".".join(str(p) for p in err.absolute_path) or "(root)"
        return f"{path}: {err.message}"

    def _resolver_tirada(self, partida: Partida, requiere: RequiereTirada) -> Tirada:
        """Resuelve una tirada declarada: tira un d20 real, suma el modificador
        de la habilidad y clasifica contra el DC fijo de la banda. Compartido por
        el path síncrono y el de streaming. Las enums vienen ya validadas por el
        schema, así que la conversión es segura."""
        habilidad = Habilidad(requiere.habilidad)
        banda = Banda(requiere.banda)
        dc = dados.dc_de_banda(banda)
        modificador = partida.personaje.atributos.modificador(habilidad)
        d20 = dados.tirar_d20(self._rng)
        resultado = dados.clasificar_tirada(d20=d20, modificador_total=modificador, dc=dc)
        return Tirada(
            habilidad=habilidad,
            banda=banda,
            dc=dc,
            d20=d20,
            modificador=modificador,
            total=d20 + modificador,
            resultado=resultado,
        )

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

        if upd.npc_encontrado and not any(n.nombre == upd.npc_encontrado.nombre for n in ws.npcs):
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
                    with contextlib.suppress(ValueError):
                        npc.actitud = Actitud(upd.npc_actitud_cambio.nueva_actitud)
                    break

        if upd.pista_descubierta:
            ws.pistas.append(upd.pista_descubierta)

        # Arco narrativo y memoria rodante: reemplazan al conteo de turnos como
        # reloj dramático y como contexto de coherencia en partidas largas.
        with contextlib.suppress(ValueError):
            ws.fase_narrativa = FaseNarrativa(turno_llm.arco.fase_narrativa)
        ws.tension = max(0, min(10, turno_llm.arco.tension))
        if turno_llm.resumen_historia:
            ws.resumen_historia = turno_llm.resumen_historia

    def _generar_imagen_segura(
        self,
        *,
        codigo_partida: str,
        turno: int,
        personaje: Personaje,
        descripcion_escena_en: str,
        genero: Genero,
        imagenes_previas: int,
        usa_referencia: bool,
    ) -> str | None:
        if imagenes_previas >= self.settings.max_imagenes_por_partida:
            logger.info("Límite de imágenes alcanzado")
            return None

        try:
            prompt = build_image_prompt(
                personaje.descripcion_visual_en, descripcion_escena_en, genero
            )
            # Flujo nuevo: anclar la escena a la referencia canónica del personaje
            # vía images.edit. Si la referencia falla, degradamos a imagen por
            # texto para igual renderizar algo (el turno no se rompe).
            ref_bytes = (
                self._asegurar_referencia_visual(codigo_partida, personaje, genero)
                if usa_referencia
                else None
            )
            if ref_bytes is not None:
                png = self.foundry.editar_imagen(prompt, ref_bytes)
            else:
                png = self.foundry.generar_imagen(prompt)
            return self.imagenes.subir_imagen(codigo_partida, turno, png)
        except Exception:
            logger.exception("Falló generación de imagen para %s", codigo_partida)
            return None

    def _asegurar_referencia_visual(
        self, codigo_partida: str, personaje: Personaje, genero: Genero
    ) -> bytes | None:
        """Garantiza la referencia visual canónica del personaje y devuelve sus
        bytes. Se genera una sola vez (memoizada en personaje.referencia_visual_url)
        y NO cuenta contra el cupo de imágenes. Devuelve None si la generación o
        descarga falla; el llamador degrada entonces a imagen por texto."""
        if personaje.referencia_visual_url:
            try:
                return self.imagenes.descargar_imagen(personaje.referencia_visual_url)
            except Exception:
                logger.exception("No se pudo descargar la referencia visual de %s", codigo_partida)
                return None

        try:
            prompt = build_reference_prompt(personaje.descripcion_visual_en, genero)
            png = self.foundry.generar_imagen(prompt)
            personaje.referencia_visual_url = self.imagenes.subir_referencia(codigo_partida, png)
            return png
        except Exception:
            logger.exception("Falló la generación de la referencia visual de %s", codigo_partida)
            return None

    def generar_imagen_turno(self, codigo_partida: str, turno_num: int) -> str:
        """Genera a demanda la imagen de un turno ya jugado."""
        partida = self.partidas.get(codigo_partida)

        if partida.metadata.imagenes_generadas >= self.settings.max_imagenes_por_partida:
            raise LimiteImagenesExcedidoError(
                f"La partida alcanzó el máximo de {self.settings.max_imagenes_por_partida} imágenes"
            )

        turno = next((t for t in partida.historial if t.turno == turno_num), None)
        if turno is None:
            raise PartidaNoEncontradaError(
                f"El turno {turno_num} no existe en la partida {codigo_partida}"
            )

        if turno.imagen_url:
            return turno.imagen_url

        if not turno.descripcion_escena_en:
            raise RespuestaLLMInvalidaError(
                f"El turno {turno_num} no tiene descripción de escena para generar imagen"
            )

        logger.info("Generando imagen a demanda: codigo=%s, turno=%s", codigo_partida, turno_num)

        imagen_url = self._generar_imagen_segura(
            codigo_partida=codigo_partida,
            turno=turno_num,
            personaje=partida.personaje,
            descripcion_escena_en=turno.descripcion_escena_en,
            genero=partida.metadata.genero,
            imagenes_previas=partida.metadata.imagenes_generadas,
            usa_referencia=partida.metadata.usa_referencia_visual,
        )
        if not imagen_url:
            raise FoundryError("Falló la generación de la imagen")

        partida.metadata.imagenes_generadas += 1
        turno.imagen_url = imagen_url
        self.partidas.upsert(partida)
        return imagen_url

    async def _stream_narrativa(
        self, system_prompt: str, user_prompt: str, sink: list[str]
    ) -> AsyncGenerator[str, None]:
        """Streamea una llamada al LLM: emite los fragmentos de `narrativa` a
        medida que llegan y deposita el JSON crudo completo en `sink`."""
        system_with_schema = (
            f"{system_prompt}\n\n# SCHEMA JSON ESPERADO\n{json.dumps(TURNO_JSON_SCHEMA, indent=2)}"
        )
        extractor = _NarrativaExtractor()
        accumulated = ""
        async for chunk in self.foundry.chat_streaming_async(system_with_schema, user_prompt):
            accumulated += chunk
            text = extractor.feed(chunk)
            if text:
                yield text
        sink.append(accumulated)

    def _parse_stream_turno(self, accumulated: str) -> TurnoLLMResponse:
        """Parsea y valida el JSON acumulado de un stream contra el schema del turno."""
        try:
            parsed = json.loads(accumulated)
        except json.JSONDecodeError as e:
            telemetry.record_llm_error(operation="chat_stream", tipo="json")
            raise RespuestaLLMInvalidaError(
                "Stream LLM devolvió JSON inválido",
                detalles={"inicio": accumulated[:200]},
            ) from e

        try:
            validate(parsed, TURNO_JSON_SCHEMA)
        except ValidationError as e:
            telemetry.record_llm_error(operation="chat_stream", tipo="schema")
            raise RespuestaLLMInvalidaError(
                f"JSON del stream no respeta el schema: {self._summarize_validation_error(e)}",
                detalles={"inicio": accumulated[:200]},
            ) from e

        return TurnoLLMResponse.model_validate(parsed)

    async def _parse_stream_con_reintento(
        self, system_prompt: str, accumulated: str
    ) -> TurnoLLMResponse:
        """Parsea el JSON streameado; si no respeta el schema, hace UN reintento
        no-streaming alimentando el error (igual que la ruta no-streaming). Evita
        que una sola violación de schema —p. ej. una opción demasiado larga— corte
        el turno y cierre el modal del dado en el cliente."""
        try:
            return self._parse_stream_turno(accumulated)
        except RespuestaLLMInvalidaError as e:
            error_msg = self._summarize_validation_error(e.__cause__) if isinstance(
                e.__cause__, ValidationError
            ) else "respuesta no es JSON parseable"
            logger.warning("Stream LLM inválido (%s); reintento no-streaming", error_msg)

        retry_user = build_retry_user_prompt(accumulated, error_msg)
        raw2, parsed2 = await asyncio.to_thread(
            self.foundry.chat_json_raw, system_prompt, retry_user
        )

        if parsed2 is None:
            telemetry.record_llm_error(operation="chat_stream", tipo="json")
            raise RespuestaLLMInvalidaError(
                "Stream LLM devolvió JSON inválido en dos intentos",
                detalles={"ultimo_intento": raw2[:500]},
            )

        try:
            validate(parsed2, TURNO_JSON_SCHEMA)
        except ValidationError as e:
            telemetry.record_llm_error(operation="chat_stream", tipo="schema")
            raise RespuestaLLMInvalidaError(
                f"Stream LLM no respetó el schema tras reintento: "
                f"{self._summarize_validation_error(e)}",
                detalles={"ultimo_intento": raw2[:500]},
            ) from e

        return TurnoLLMResponse.model_validate(parsed2)

    async def avanzar_turno_stream(
        self, codigo_partida: str, accion: str
    ) -> AsyncGenerator[str, None]:
        """SSE stream con un span por turno (envuelve la generación interna)."""
        with telemetry.get_tracer().start_as_current_span("avanzar_turno_stream") as span:
            span.set_attribute("codigo_partida", codigo_partida)
            span.set_attribute("prompt_version", PROMPT_VERSION)
            async for evento in self._avanzar_turno_stream_impl(codigo_partida, accion):
                yield evento

    async def _avanzar_turno_stream_impl(
        self, codigo_partida: str, accion: str
    ) -> AsyncGenerator[str, None]:
        """SSE stream: yields token/turno/imagen/done events."""

        def _sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        partida = await asyncio.to_thread(self.partidas.get, codigo_partida)

        if partida.metadata.estado == EstadoPartida.FINALIZADA:
            raise PartidaFinalizadaError(
                f"La partida {codigo_partida} ya terminó",
                detalles={"final": partida.metadata.final},
            )

        logger.info(
            "Avanzando turno (stream): codigo=%s, turno_actual=%s, prompt_version=%s",
            codigo_partida,
            partida.metadata.turno_actual,
            PROMPT_VERSION,
        )

        # Fase 1: streameamos el turno. Si el narrador declara una tirada, esta
        # narración es la preparación; tras tirar, la fase 2 streamea el desenlace
        # y reemplaza al turno autoritativo. El frontend resetea la narrativa al
        # recibir el evento `tirada`.
        # El turno se entrega de forma atómica: NO emitimos los tokens parciales.
        # Cuando hay tirada, la fase 1 es preparación que se descarta, y mostrarla
        # antes de la tirada confundía (el narrador "cambiaba" al resolver). El
        # cliente revela la narrativa final del turno una sola vez.
        user = build_turno_user_prompt(partida, accion)
        sink: list[str] = []
        async for _ in self._stream_narrativa(SYSTEM_PROMPT_TURNO, user, sink):
            pass
        turno_llm = await self._parse_stream_con_reintento(SYSTEM_PROMPT_TURNO, sink[0])

        tirada = None
        if turno_llm.requiere_tirada is not None:
            tirada = self._resolver_tirada(partida, turno_llm.requiere_tirada)
            # La tirada se emite ANTES de generar el desenlace: el cliente abre el
            # modal del dado mientras la fase 2 se genera en paralelo.
            yield _sse("tirada", _tirada_a_dict(tirada))
            user2 = build_resolucion_user_prompt(partida, accion, tirada)
            sink2: list[str] = []
            async for _ in self._stream_narrativa(SYSTEM_PROMPT_RESOLUCION, user2, sink2):
                pass
            turno_llm = await self._parse_stream_con_reintento(SYSTEM_PROMPT_RESOLUCION, sink2[0])

        nuevo_turno_num = partida.metadata.turno_actual + 1
        es_final = turno_llm.estado_aventura.tipo == "finalizada"
        self._aplicar_actualizaciones(partida, turno_llm)

        # Persist turn (without image URL yet)
        descripcion_escena = turno_llm.generar_imagen.descripcion_escena_en
        nuevo_turno = TurnoHistorial(
            turno=nuevo_turno_num,
            accion_jugador=accion,
            narrativa=turno_llm.narrativa,
            opciones=list(turno_llm.opciones),
            imagen_url=None,
            descripcion_escena_en=descripcion_escena,
            tirada=tirada,
        )
        partida.historial.append(nuevo_turno)
        partida.metadata.turno_actual = nuevo_turno_num
        partida.metadata.actualizada_en = datetime.now(UTC)

        if es_final:
            partida.metadata.estado = EstadoPartida.FINALIZADA
            if turno_llm.estado_aventura.final:
                with contextlib.suppress(ValueError):
                    partida.metadata.final = TipoFinal(turno_llm.estado_aventura.final)
            partida.metadata.razon_fin = turno_llm.estado_aventura.razon_fin

        await asyncio.to_thread(self.partidas.upsert, partida)

        # Solo el último turno genera imagen automáticamente; el resto a demanda.
        imagen_solicitada = es_final and bool(descripcion_escena)

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
                "tirada": _tirada_a_dict(tirada) if tirada else None,
            },
        )

        # Generate image asynchronously (SSE connection stays open)
        if imagen_solicitada:
            imagen_url = await asyncio.to_thread(
                self._generar_imagen_segura,
                codigo_partida=codigo_partida,
                turno=nuevo_turno_num,
                personaje=partida.personaje,
                descripcion_escena_en=turno_llm.generar_imagen.descripcion_escena_en,
                genero=partida.metadata.genero,
                imagenes_previas=partida.metadata.imagenes_generadas,
                usa_referencia=partida.metadata.usa_referencia_visual,
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


def _tirada_a_dict(tirada: Tirada) -> dict:
    """Serializa una Tirada para el evento SSE `tirada` (y respuestas de turno)."""
    return {
        "habilidad": tirada.habilidad.value,
        "banda": tirada.banda.value,
        "dc": tirada.dc,
        "d20": tirada.d20,
        "modificador": tirada.modificador,
        "total": tirada.total,
        "resultado": tirada.resultado.value,
    }


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
