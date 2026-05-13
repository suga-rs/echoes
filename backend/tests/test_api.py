"""Tests de los endpoints HTTP usando TestClient."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_partida_service
from app.main import app
from app.models.domain import (
    EstadoPartida,
    Genero,
    MetadataPartida,
    Partida,
    Personaje,
    StartResponse,
    TurnoResponse,
    WorldState,
)


@pytest.fixture
def client_con_servicio_mockeado():
    service_mock = MagicMock()

    def override_get_service():
        return service_mock

    app.dependency_overrides[get_partida_service] = override_get_service
    client = TestClient(app)
    yield client, service_mock
    app.dependency_overrides.clear()


def test_healthz(client_con_servicio_mockeado):
    client, _ = client_con_servicio_mockeado
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_start_partida(client_con_servicio_mockeado):
    client, svc = client_con_servicio_mockeado
    svc.crear_partida.return_value = StartResponse(
        codigo_partida="abc-123-xyz",
        personaje=Personaje(
            nombre="Lyra",
            descripcion_narrativa="Test",
            descripcion_visual_en="Tall woman with red hair wearing leather armor",
        ),
        objetivo="Encontrar la espada",
        primer_turno=TurnoResponse(
            turno=1,
            narrativa="Empezás tu aventura...",
            opciones=["A", "B", "C"],
            imagen_url="https://fake/x.png",
            estado=EstadoPartida.EN_CURSO,
        ),
    )

    r = client.post(
        "/api/partidas/start",
        json={
            "genero": "fantasía",
            "descripcion_personaje": "una arqueóloga escéptica de 40 años",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["codigo_partida"] == "abc-123-xyz"


def test_start_partida_validacion_corta(client_con_servicio_mockeado):
    client, _ = client_con_servicio_mockeado
    r = client.post(
        "/api/partidas/start",
        json={"genero": "fantasía", "descripcion_personaje": "abc"},
    )
    assert r.status_code == 422


def test_avanzar_turno(client_con_servicio_mockeado):
    client, svc = client_con_servicio_mockeado
    svc.avanzar_turno.return_value = TurnoResponse(
        turno=2,
        narrativa="Avanzás con cuidado.",
        opciones=["A", "B", "C"],
        imagen_url=None,
        estado=EstadoPartida.EN_CURSO,
    )

    r = client.post(
        "/api/partidas/abc-123/turn",
        json={"accion": "Acercarme a la vela"},
    )
    assert r.status_code == 200
    assert r.json()["turno"] == 2


def test_partida_no_encontrada_devuelve_404(client_con_servicio_mockeado):
    from app.core.exceptions import PartidaNoEncontrada

    client, svc = client_con_servicio_mockeado
    svc.get_partida.side_effect = PartidaNoEncontrada("No existe")

    r = client.get("/api/partidas/fake-code/state")
    assert r.status_code == 404
    assert r.json()["code"] == "partida_no_encontrada"


def test_state_endpoint(client_con_servicio_mockeado):
    client, svc = client_con_servicio_mockeado
    svc.get_partida.return_value = Partida(
        id="abc",
        codigo_partida="abc",
        metadata=MetadataPartida(
            genero=Genero.FANTASIA,
            creada_en=datetime.now(UTC),
            turno_actual=5,
            estado=EstadoPartida.EN_CURSO,
        ),
        personaje=Personaje(
            nombre="Lyra",
            descripcion_narrativa="Test",
            descripcion_visual_en="Test visual description that is long enough now",
            inventario=["linterna", "diario"],
        ),
        world_state=WorldState(
            ubicacion_actual="Cripta",
            objetivo="Encontrar el corazón",
            eventos_clave=["evento 1"],
        ),
    )

    r = client.get("/api/partidas/abc/state")
    assert r.status_code == 200
    data = r.json()
    assert data["turno_actual"] == 5
    assert data["personaje_nombre"] == "Lyra"
    assert "linterna" in data["inventario"]
