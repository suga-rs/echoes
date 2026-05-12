"""Dependencias de FastAPI para inyección."""

from functools import lru_cache

from app.services.partida_service import PartidaService


@lru_cache
def get_partida_service() -> PartidaService:
    return PartidaService()
