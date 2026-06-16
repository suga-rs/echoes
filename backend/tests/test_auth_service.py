"""Tests del AuthService con repositorios mockeados."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import CredencialesInvalidasError, UsuarioYaExisteError
from app.core.security import decode_access_token, hash_password
from app.models.domain import Usuario
from app.services.auth_service import AuthService


@pytest.fixture
def usuario_repo_mock() -> MagicMock:
    return MagicMock()


@pytest.fixture
def auth_service(usuario_repo_mock) -> AuthService:
    return AuthService(
        usuarios=usuario_repo_mock,
        partidas=MagicMock(),
        imagenes=MagicMock(),
    )


def test_register_ok(auth_service, usuario_repo_mock):
    usuario_repo_mock.get_by_username.return_value = None

    resp = auth_service.register("Nuevo", "contraseña123")

    assert resp.user.username == "Nuevo"
    assert decode_access_token(resp.access_token) == resp.user.id
    usuario_repo_mock.create.assert_called_once()
    # El usuario público no expone el hash.
    assert not hasattr(resp.user, "password_hash")


def test_register_duplicate(auth_service, usuario_repo_mock):
    usuario_repo_mock.get_by_username.return_value = Usuario(
        id="x",
        username="Existente",
        username_lower="existente",
        password_hash="h",
        creada_en=datetime.now(UTC),
    )
    with pytest.raises(UsuarioYaExisteError):
        auth_service.register("Existente", "contraseña123")


def test_register_creator_reserved(auth_service, usuario_repo_mock):
    usuario_repo_mock.get_by_username.return_value = None
    with pytest.raises(UsuarioYaExisteError):
        auth_service.register("creator", "contraseña123")
    usuario_repo_mock.create.assert_not_called()


def test_login_ok(auth_service, usuario_repo_mock):
    usuario_repo_mock.get_by_username.return_value = Usuario(
        id="u1",
        username="Lyra",
        username_lower="lyra",
        password_hash=hash_password("contraseña123"),
        creada_en=datetime.now(UTC),
    )
    resp = auth_service.login("Lyra", "contraseña123")
    assert decode_access_token(resp.access_token) == "u1"


def test_login_wrong_password(auth_service, usuario_repo_mock):
    usuario_repo_mock.get_by_username.return_value = Usuario(
        id="u1",
        username="Lyra",
        username_lower="lyra",
        password_hash=hash_password("contraseña123"),
        creada_en=datetime.now(UTC),
    )
    with pytest.raises(CredencialesInvalidasError):
        auth_service.login("Lyra", "incorrecta")


def test_login_unknown_user_same_error(auth_service, usuario_repo_mock):
    usuario_repo_mock.get_by_username.return_value = None
    with pytest.raises(CredencialesInvalidasError):
        auth_service.login("Fantasma", "loquesea123")
