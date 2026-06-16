"""Tests de los endpoints de auth y perfil usando TestClient."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_auth_service
from app.core.security import create_access_token
from app.main import app
from app.models.domain import AuthResponse, PerfilResponse, UsuarioPublico


@pytest.fixture
def client_auth():
    service_mock = MagicMock()
    app.dependency_overrides[get_auth_service] = lambda: service_mock
    client = TestClient(app)
    yield client, service_mock
    app.dependency_overrides.clear()


def _publico() -> UsuarioPublico:
    return UsuarioPublico(id="u1", username="Lyra", creada_en=datetime.now(UTC), avatar_url=None)


def test_register_endpoint(client_auth):
    client, svc = client_auth
    svc.register.return_value = AuthResponse(access_token="tok", user=_publico())
    r = client.post("/api/auth/register", json={"username": "Lyra", "password": "contraseña123"})
    assert r.status_code == 201
    assert r.json()["access_token"] == "tok"
    assert "password_hash" not in r.json()["user"]


def test_login_endpoint(client_auth):
    client, svc = client_auth
    svc.login.return_value = AuthResponse(access_token="tok", user=_publico())
    r = client.post("/api/auth/login", json={"username": "Lyra", "password": "contraseña123"})
    assert r.status_code == 200
    assert r.json()["access_token"] == "tok"


def test_perfil_sin_token_401(client_auth):
    client, _ = client_auth
    r = client.get("/api/usuarios/me")
    assert r.status_code == 401


def test_perfil_con_token_excluye_hash(client_auth):
    client, svc = client_auth
    svc.get_perfil.return_value = PerfilResponse(user=_publico(), partidas=[])
    token = create_access_token("u1")
    r = client.get("/api/usuarios/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "password_hash" not in r.json()["user"]
    svc.get_perfil.assert_called_once_with("u1")


def test_avatar_sin_token_401(client_auth):
    client, _ = client_auth
    r = client.post("/api/usuarios/me/avatar", files={"file": ("a.png", b"x", "image/png")})
    assert r.status_code == 401


def test_avatar_tipo_invalido_422(client_auth):
    from app.core.exceptions import ContenidoInapropiadoError

    client, svc = client_auth
    svc.set_avatar.side_effect = ContenidoInapropiadoError("Formato no soportado")
    token = create_access_token("u1")
    r = client.post(
        "/api/usuarios/me/avatar",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("a.txt", b"x", "text/plain")},
    )
    assert r.status_code == 422
