"""Utilidades de seguridad: hashing de contraseñas (bcrypt) y JWT (HS256).

Usamos `bcrypt` directamente en lugar de `passlib` por una incompatibilidad
conocida entre passlib 1.7.4 y bcrypt >= 4.1 (passlib ejecuta un self-test con
una contraseña de >72 bytes que bcrypt 5.x rechaza).
"""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import Settings, get_settings

# bcrypt opera solo sobre los primeros 72 bytes de la contraseña.
_MAX_BCRYPT_BYTES = 72


def _to_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_MAX_BCRYPT_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_to_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_to_bytes(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings | None = None) -> str | None:
    """Devuelve el `user_id` (claim `sub`) si el token es válido, o None si es
    inválido / expirado / manipulado."""
    settings = settings or get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    sub = payload.get("sub")
    return sub if isinstance(sub, str) else None
