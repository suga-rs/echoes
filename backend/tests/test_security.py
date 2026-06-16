"""Tests de utilidades de seguridad: hashing y JWT."""

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_verify_round_trip():
    h = hash_password("contraseña-secreta")
    assert h != "contraseña-secreta"
    assert verify_password("contraseña-secreta", h) is True
    assert verify_password("otra-cosa", h) is False


def test_hash_is_salted():
    # Dos hashes de la misma contraseña deben diferir (salt aleatorio).
    assert hash_password("misma") != hash_password("misma")


def test_token_encode_decode():
    token = create_access_token("user-42")
    assert decode_access_token(token) == "user-42"


def test_token_tampered_rejected():
    token = create_access_token("user-42")
    assert decode_access_token(token + "tampered") is None


def test_token_expired_rejected():
    settings = get_settings().model_copy(update={"jwt_expire_minutes": -1})
    token = create_access_token("user-42", settings)
    assert decode_access_token(token) is None


def test_token_wrong_secret_rejected():
    settings = get_settings().model_copy(update={"jwt_secret": "otro-secreto-distinto-largo"})
    token = create_access_token("user-42", settings)
    # Decodificado con el secreto por defecto: inválido.
    assert decode_access_token(token) is None
