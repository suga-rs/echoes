"""Endpoints HTTP de partidas."""

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_partida_service
from app.core.logging import get_logger
from app.models.domain import (
    StartPartidaRequest, StartResponse, StateResponse,
    TurnoRequest, TurnoResponse,
)
from app.services.partida_service import PartidaService

logger = get_logger("api.partidas")

router = APIRouter(prefix="/api/partidas", tags=["partidas"])


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
    codigo: str, body: TurnoRequest,
    service: PartidaService = Depends(get_partida_service),
) -> TurnoResponse:
    return service.avanzar_turno(codigo, body.accion)


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
