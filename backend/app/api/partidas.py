"""Endpoints HTTP de partidas."""

import json

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_partida_service
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.models.domain import (
    PartidaResumen,
    RandomDescriptionRequest,
    RandomDescriptionResponse,
    StartPartidaRequest,
    StartResponse,
    StateResponse,
    TurnoRequest,
    TurnoResponse,
)
from app.services.partida_service import PartidaService

logger = get_logger("api.partidas")

router = APIRouter(prefix="/api/partidas", tags=["partidas"])


@router.get("", response_model=list[PartidaResumen])
def listar_partidas(
    service: PartidaService = Depends(get_partida_service),
) -> list[PartidaResumen]:
    return service.listar_partidas()


@router.post("/random-description", response_model=RandomDescriptionResponse)
def random_description(
    body: RandomDescriptionRequest,
    service: PartidaService = Depends(get_partida_service),
) -> RandomDescriptionResponse:
    descripcion = service.generar_descripcion_aleatoria(body.genero)
    return RandomDescriptionResponse(descripcion=descripcion)


@router.post("/start", response_model=StartResponse, status_code=status.HTTP_201_CREATED)
def start_partida(
    body: StartPartidaRequest,
    service: PartidaService = Depends(get_partida_service),
) -> StartResponse:
    return service.crear_partida(
        genero=body.genero,
        descripcion_personaje=body.descripcion_personaje,
    )


@router.post("/{codigo}/turn", response_model=TurnoResponse)
def avanzar_turno(
    codigo: str,
    body: TurnoRequest,
    service: PartidaService = Depends(get_partida_service),
) -> TurnoResponse:
    return service.avanzar_turno(codigo, body.accion)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/{codigo}/turn/stream")
async def avanzar_turno_stream(
    codigo: str,
    body: TurnoRequest,
    service: PartidaService = Depends(get_partida_service),
) -> StreamingResponse:
    async def generate():
        try:
            async for chunk in service.avanzar_turno_stream(codigo, body.accion):
                yield chunk
        except AppError as e:
            yield _sse("error", {"code": e.code, "mensaje": e.mensaje})
        except Exception:
            logger.exception("Error inesperado en stream de turno")
            yield _sse("error", {"code": "internal_error", "mensaje": "Error inesperado"})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{codigo}/resume")
def resume_partida(
    codigo: str,
    service: PartidaService = Depends(get_partida_service),
):
    return service.get_partida(codigo)


@router.get("/{codigo}/state", response_model=StateResponse)
def get_state(
    codigo: str,
    service: PartidaService = Depends(get_partida_service),
) -> StateResponse:
    p = service.get_partida(codigo)
    return StateResponse(
        codigo_partida=p.codigo_partida,
        turno_actual=p.metadata.turno_actual,
        estado=p.metadata.estado,
        personaje_nombre=p.personaje.nombre,
        inventario=p.personaje.inventario,
        ubicacion=p.world_state.ubicacion_actual,
        objetivo=p.world_state.objetivo,
        eventos_clave=p.world_state.eventos_clave,
        npcs_conocidos=[n.nombre for n in p.world_state.npcs],
    )
