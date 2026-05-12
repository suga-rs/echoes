"""Servicio de partidas: orquesta LLM, imagen, persistencia."""

import secrets
from datetime import datetime, timezone

from jsonschema import ValidationError, validate

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    LimiteTurnosExcedido, PartidaFinalizada, RespuestaLLMInvalida,
)
from app.core.logging import get_logger
from app.models.domain import (
    Actitud, EstadoPartida, Genero, MetadataPartida, NPC, Partida,
    Personaje, StartResponse, TipoFinal, TurnoHistorial, TurnoResponse,
    WorldState,
)
from app.models.llm_schema import (
    CREACION_JSON_SCHEMA, CreacionLLMResponse,
    TURNO_JSON_SCHEMA, TurnoLLMResponse,
)
from app.repositories.imagen_repo import ImagenRepository
from app.repositories.partida_repo import PartidaRepository
from app.services.foundry_client import FoundryClient
from app.services.prompts import (
    SYSTEM_PROMPT_CREACION, SYSTEM_PROMPT_TURNO,
    build_creacion_user_prompt, build_image_prompt,
    build_retry_user_prompt, build_turno_user_prompt,
)

logger = get_logger("service.partidas")


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

    def crear_partida(
        self, genero: Genero, descripcion_personaje: str
    ) -> StartResponse:
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
            creada_en=datetime.now(timezone.utc),
            turno_actual=1,
            estado=EstadoPartida.EN_CURSO,
        )

        imagen_url = self._generar_imagen_segura(
            codigo_partida=codigo, turno=1,
            descripcion_visual_personaje_en=personaje.descripcion_visual_en,
            descripcion_escena_en=creacion.primera_escena.descripcion_imagen_en,
            genero=genero, imagenes_previas=0,
        )

        primer_turno = TurnoHistorial(
            turno=1, accion_jugador="<inicio>",
            narrativa=creacion.primera_escena.narrativa,
            opciones=list(creacion.primera_escena.opciones),
            imagen_url=imagen_url,
        )
        if imagen_url:
            metadata.imagenes_generadas = 1

        partida = Partida(
            id=codigo, codigo_partida=codigo,
            metadata=metadata, personaje=personaje,
            world_state=world_state, historial=[primer_turno],
        )
        self.partidas.upsert(partida)
        logger.info("Partida creada: codigo=%s", codigo)

        return StartResponse(
            codigo_partida=codigo, personaje=personaje,
            objetivo=world_state.objetivo,
            primer_turno=TurnoResponse(
                turno=1, narrativa=primer_turno.narrativa,
                opciones=primer_turno.opciones, imagen_url=imagen_url,
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
                f"La partida alcanzó el máximo de "
                f"{self.settings.max_turnos_por_partida} turnos"
            )

        logger.info(
            "Avanzando turno: codigo=%s, turno_actual=%s",
            codigo_partida, partida.metadata.turno_actual,
        )

        system = SYSTEM_PROMPT_TURNO
        user = build_turno_user_prompt(partida, accion)
        turno_llm = self._invocar_llm_con_reintento(
            system, user, TURNO_JSON_SCHEMA, TurnoLLMResponse
        )

        nuevo_turno_num = partida.metadata.turno_actual + 1
        self._aplicar_actualizaciones(partida, turno_llm)

        imagen_url = None
        if (turno_llm.generar_imagen.necesaria and
                turno_llm.generar_imagen.descripcion_escena_en):
            imagen_url = self._generar_imagen_segura(
                codigo_partida=codigo_partida, turno=nuevo_turno_num,
                descripcion_visual_personaje_en=partida.personaje.descripcion_visual_en,
                descripcion_escena_en=turno_llm.generar_imagen.descripcion_escena_en,
                genero=partida.metadata.genero,
                imagenes_previas=partida.metadata.imagenes_generadas,
            )
            if imagen_url:
                partida.metadata.imagenes_generadas += 1

        nuevo_turno = TurnoHistorial(
            turno=nuevo_turno_num, accion_jugador=accion,
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
            turno=nuevo_turno_num, narrativa=turno_llm.narrativa,
            opciones=list(turno_llm.opciones), imagen_url=imagen_url,
            estado=partida.metadata.estado, final=partida.metadata.final,
            razon_fin=partida.metadata.razon_fin,
        )

    def get_partida(self, codigo_partida: str) -> Partida:
        return self.partidas.get(codigo_partida)

    def _invocar_llm_con_reintento(
        self, system_prompt: str, user_prompt: str,
        json_schema: dict, modelo_pydantic: type,
    ):
        import json
        # Inyectamos el schema en el prompt del sistema para que el LLM sepa que devolver.
        system_with_schema = f"{system_prompt}\n\n# SCHEMA JSON ESPERADO\n{json.dumps(json_schema, indent=2)}"

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

    def _aplicar_actualizaciones(
        self, partida: Partida, turno_llm: TurnoLLMResponse
    ) -> None:
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
                ws.npcs.append(NPC(
                    nombre=upd.npc_encontrado.nombre,
                    descripcion=upd.npc_encontrado.descripcion,
                    actitud=actitud,
                ))

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
        self, *, codigo_partida: str, turno: int,
        descripcion_visual_personaje_en: str,
        descripcion_escena_en: str, genero: Genero,
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

    @staticmethod
    def _generar_codigo_partida() -> str:
        alphabet = "abcdefghijkmnpqrstuvwxyz23456789"
        groups = [
            "".join(secrets.choice(alphabet) for _ in range(4))
            for _ in range(3)
        ]
        return "-".join(groups)
