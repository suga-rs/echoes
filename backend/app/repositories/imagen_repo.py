"""Repositorio para subir imágenes generadas a Blob Storage."""

import uuid

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger("repo.imagenes")


class ImagenRepository:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._service = self._build_service()
        self._container = self._service.get_container_client(self.settings.storage_container)
        self._avatares = self._service.get_container_client(
            self.settings.storage_avatares_container
        )

    def _build_service(self) -> BlobServiceClient:
        if self.settings.storage_connection_string:
            logger.info("Blob: usando connection string")
            return BlobServiceClient.from_connection_string(self.settings.storage_connection_string)
        account_url = f"https://{self.settings.storage_account_name}.blob.core.windows.net"
        logger.info("Blob: usando Entra ID con %s", account_url)
        return BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())

    def subir_imagen(self, codigo_partida: str, turno: int, contenido: bytes) -> str:
        nombre = f"{codigo_partida}/turno-{turno:03d}-{uuid.uuid4().hex[:8]}.png"
        blob = self._container.get_blob_client(nombre)
        blob.upload_blob(
            contenido,
            overwrite=True,
            content_settings=ContentSettings(content_type="image/png"),
        )
        url = blob.url
        logger.info("Imagen subida: %s", url)
        return url

    def subir_referencia(self, codigo_partida: str, contenido: bytes) -> str:
        # Nombre fijo por partida + overwrite: la referencia canónica del
        # personaje se genera una sola vez y se reutiliza en cada imagen.
        nombre = f"{codigo_partida}/referencia.png"
        blob = self._container.get_blob_client(nombre)
        blob.upload_blob(
            contenido,
            overwrite=True,
            content_settings=ContentSettings(content_type="image/png"),
        )
        url = blob.url
        logger.info("Referencia de personaje subida: %s", url)
        return url

    def descargar_imagen(self, url: str) -> bytes:
        # El URL es {container.url}/{nombre}; derivamos el nombre para reutilizar
        # el cliente autenticado del contenedor (el contenedor puede ser privado).
        prefijo = self._container.url.rstrip("/") + "/"
        nombre = url[len(prefijo) :] if url.startswith(prefijo) else url.rsplit("/", 1)[-1]
        blob = self._container.get_blob_client(nombre)
        return blob.download_blob().readall()

    def eliminar_imagenes(self, codigo_partida: str) -> None:
        """Borra todos los blobs de una partida (imágenes por turno + referencia
        del personaje), que comparten el prefijo `{codigo_partida}/`. Best-effort:
        loguea y continúa ante fallos individuales para que la eliminación del
        documento siga su curso."""
        prefijo = f"{codigo_partida}/"
        try:
            nombres = [b.name for b in self._container.list_blobs(name_starts_with=prefijo)]
        except Exception:
            logger.exception("No se pudieron listar imágenes de %s", codigo_partida)
            return
        for nombre in nombres:
            try:
                self._container.delete_blob(nombre)
            except Exception:
                logger.exception("No se pudo borrar el blob %s", nombre)
        logger.info("Imágenes eliminadas para %s (%d blobs)", codigo_partida, len(nombres))

    def subir_avatar(self, user_id: str, contenido: bytes, ext: str, content_type: str) -> str:
        # Nombre fijo por usuario + overwrite: cada subida reemplaza la anterior.
        nombre = f"avatar/{user_id}.{ext}"
        blob = self._avatares.get_blob_client(nombre)
        blob.upload_blob(
            contenido,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        url = blob.url
        logger.info("Avatar subido: %s", url)
        return url
