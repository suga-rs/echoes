"""Servicio de autenticación y perfil de usuario."""

import uuid
from datetime import UTC, datetime

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    ContenidoInapropiadoError,
    CredencialesInvalidasError,
    NoAutenticadoError,
    UsuarioYaExisteError,
)
from app.core.logging import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.models.domain import (
    AuthResponse,
    PerfilResponse,
    Usuario,
    UsuarioPublico,
)
from app.repositories.imagen_repo import ImagenRepository
from app.repositories.partida_repo import PartidaRepository
from app.repositories.usuario_repo import UsuarioRepository

logger = get_logger("service.auth")

# Identidad reservada para el usuario built-in que posee las partidas anónimas
# y las previas a la introducción de cuentas.
CREATOR_ID = "0"
CREATOR_USERNAME = "Creator"

_AVATAR_CONTENT_TYPES: dict[str, str] = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}
_MAX_AVATAR_BYTES = 5 * 1024 * 1024  # 5 MB


class AuthService:
    def __init__(
        self,
        usuarios: UsuarioRepository | None = None,
        partidas: PartidaRepository | None = None,
        imagenes: ImagenRepository | None = None,
        settings: Settings | None = None,
    ):
        self.settings = settings or get_settings()
        self.usuarios = usuarios or UsuarioRepository(self.settings)
        self.partidas = partidas or PartidaRepository(self.settings)
        self.imagenes = imagenes or ImagenRepository(self.settings)

    def register(self, username: str, password: str) -> AuthResponse:
        username = username.strip()
        username_lower = username.lower()

        # La cuenta Creator está reservada y no puede crearse por registro.
        if username_lower == CREATOR_USERNAME.lower():
            raise UsuarioYaExisteError("El nombre de usuario 'Creator' está reservado")

        if self.usuarios.get_by_username(username_lower) is not None:
            raise UsuarioYaExisteError(f"Ya existe un usuario con username '{username}'")

        usuario = Usuario(
            id=uuid.uuid4().hex,
            username=username,
            username_lower=username_lower,
            password_hash=hash_password(password),
            creada_en=datetime.now(UTC),
            avatar_url=None,
        )
        self.usuarios.create(usuario)
        logger.info("Usuario registrado: id=%s", usuario.id)

        token = create_access_token(usuario.id, self.settings)
        return AuthResponse(access_token=token, user=self._publico(usuario))

    def login(self, username: str, password: str) -> AuthResponse:
        username_lower = username.strip().lower()
        usuario = self.usuarios.get_by_username(username_lower)
        # Mismo mensaje para usuario inexistente y contraseña incorrecta: no
        # revelamos si el username existe.
        if usuario is None or not verify_password(password, usuario.password_hash):
            raise CredencialesInvalidasError("Usuario o contraseña incorrectos")

        token = create_access_token(usuario.id, self.settings)
        logger.info("Login: id=%s", usuario.id)
        return AuthResponse(access_token=token, user=self._publico(usuario))

    def get_perfil(self, user_id: str) -> PerfilResponse:
        usuario = self.usuarios.get(user_id)
        if usuario is None:
            raise NoAutenticadoError("Usuario no encontrado")
        partidas = self.partidas.list_all(user_id=user_id)
        return PerfilResponse(user=self._publico(usuario), partidas=partidas)

    def set_avatar(self, user_id: str, contenido: bytes, content_type: str) -> str:
        ext = _AVATAR_CONTENT_TYPES.get((content_type or "").lower())
        if ext is None:
            raise ContenidoInapropiadoError(
                "Formato de avatar no soportado (usar PNG, JPEG o WebP)"
            )
        if len(contenido) > _MAX_AVATAR_BYTES:
            raise ContenidoInapropiadoError("El avatar supera el tamaño máximo (5 MB)")

        usuario = self.usuarios.get(user_id)
        if usuario is None:
            raise NoAutenticadoError("Usuario no encontrado")

        url = self.imagenes.subir_avatar(user_id, contenido, ext, content_type)
        usuario.avatar_url = url
        self.usuarios.upsert(usuario)
        logger.info("Avatar actualizado: id=%s", user_id)
        return url

    @staticmethod
    def _publico(usuario: Usuario) -> UsuarioPublico:
        return UsuarioPublico(
            id=usuario.id,
            username=usuario.username,
            creada_en=usuario.creada_en,
            avatar_url=usuario.avatar_url,
        )
