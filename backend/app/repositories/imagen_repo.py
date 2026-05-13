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
