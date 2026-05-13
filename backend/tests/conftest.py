"""Fixtures comunes."""

import os
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("FOUNDRY_ENDPOINT", "https://fake.cognitiveservices.azure.com/")
os.environ.setdefault("FOUNDRY_API_KEY", "fake-key")
os.environ.setdefault("LLM_DEPLOYMENT", "fake-llm")
os.environ.setdefault("IMAGE_DEPLOYMENT", "fake-img")
os.environ.setdefault("COSMOS_ENDPOINT", "https://fake.documents.azure.com:443/")
os.environ.setdefault("COSMOS_KEY", "fake-cosmos-key")
os.environ.setdefault("STORAGE_ACCOUNT_NAME", "fakestorage")
os.environ.setdefault(
    "STORAGE_CONNECTION_STRING",
    "DefaultEndpointsProtocol=https;AccountName=fakestorage;"
    "AccountKey=fake;EndpointSuffix=core.windows.net",
)

from app.models.domain import (
    EstadoPartida,
    Genero,
    MetadataPartida,
    Partida,
    Personaje,
    WorldState,
)


@pytest.fixture
def partida_de_ejemplo() -> Partida:
    return Partida(
        id="test-abc-123",
        codigo_partida="test-abc-123",
        metadata=MetadataPartida(
            genero=Genero.FANTASIA,
            creada_en=datetime.now(UTC),
            turno_actual=1,
            estado=EstadoPartida.EN_CURSO,
        ),
        personaje=Personaje(
            nombre="Lyra",
            descripcion_narrativa="Arqueóloga escéptica de 40 años.",
            descripcion_visual_en=(
                "Woman around 40, Mediterranean features, dark brown wavy hair, "
                "hazel eyes, athletic build. Olive canvas field jacket."
            ),
            inventario=["linterna", "diario"],
        ),
        world_state=WorldState(
            ubicacion_actual="Entrada de la cripta",
            objetivo="Encontrar el corazón de la montaña",
        ),
    )


@pytest.fixture
def foundry_mock() -> MagicMock:
    return MagicMock()


@pytest.fixture
def partida_repo_mock() -> MagicMock:
    return MagicMock()


@pytest.fixture
def imagen_repo_mock() -> MagicMock:
    return MagicMock()
