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
# Fijamos los límites para que los tests sean herméticos y no dependan del
# .env local del desarrollador (las env vars tienen prioridad sobre .env).
os.environ.setdefault("MAX_IMAGENES_POR_PARTIDA", "25")
os.environ.setdefault("LLM_MAX_RETRIES", "2")
os.environ.setdefault("LLM_RETRY_BASE_DELAY", "0.01")

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.models.domain import (
    EstadoPartida,
    Genero,
    MetadataPartida,
    Partida,
    Personaje,
    WorldState,
)

# Providers OTel in-memory para testear spans y métricas sin Azure. Se instalan
# una sola vez al importar conftest (set_*_provider ignora reasignaciones).
SPAN_EXPORTER = InMemorySpanExporter()
_tracer_provider = TracerProvider()
_tracer_provider.add_span_processor(SimpleSpanProcessor(SPAN_EXPORTER))
trace.set_tracer_provider(_tracer_provider)

METRIC_READER = InMemoryMetricReader()
metrics.set_meter_provider(MeterProvider(metric_readers=[METRIC_READER]))


@pytest.fixture
def span_exporter() -> InMemorySpanExporter:
    SPAN_EXPORTER.clear()
    return SPAN_EXPORTER


@pytest.fixture
def metric_reader() -> InMemoryMetricReader:
    return METRIC_READER


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
