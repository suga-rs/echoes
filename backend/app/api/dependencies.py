"""Dependencias de FastAPI para inyección."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import NoAutenticadoError
from app.core.security import decode_access_token
from app.services.auth_service import AuthService
from app.services.partida_service import PartidaService

# auto_error=False: dejamos que cada dependencia decida si la ausencia de token
# es un error (endpoints protegidos) o significa "anónimo" (opcionales).
_bearer = HTTPBearer(auto_error=False)


@lru_cache
def get_partida_service() -> PartidaService:
    return PartidaService()


@lru_cache
def get_auth_service() -> AuthService:
    return AuthService()


def get_optional_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str | None:
    """Resuelve el user_id desde el token. Sin token → None (anónimo).
    Token presente pero inválido/expirado → 401."""
    if creds is None:
        return None
    user_id = decode_access_token(creds.credentials)
    if user_id is None:
        raise NoAutenticadoError("Token inválido o expirado")
    return user_id


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
    """Exige un token válido. Sin token o inválido → 401."""
    if creds is None:
        raise NoAutenticadoError("Se requiere autenticación")
    user_id = decode_access_token(creds.credentials)
    if user_id is None:
        raise NoAutenticadoError("Token inválido o expirado")
    return user_id
