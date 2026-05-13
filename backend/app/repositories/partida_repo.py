"""Repositorio de partidas en Cosmos DB."""

from azure.cosmos import CosmosClient, exceptions
from azure.cosmos.container import ContainerProxy
from azure.identity import DefaultAzureCredential

from app.core.config import Settings, get_settings
from app.core.exceptions import PartidaNoEncontrada
from app.core.logging import get_logger
from app.models.domain import Partida, PartidaResumen

logger = get_logger("repo.partidas")


class PartidaRepository:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._container = self._build_container()

    def _build_container(self) -> ContainerProxy:
        if self.settings.cosmos_key:
            logger.info("Cosmos: usando key")
            client = CosmosClient(self.settings.cosmos_endpoint, self.settings.cosmos_key)
        else:
            logger.info("Cosmos: usando Entra ID")
            client = CosmosClient(
                self.settings.cosmos_endpoint, credential=DefaultAzureCredential()
            )
        db = client.get_database_client(self.settings.cosmos_database)
        return db.get_container_client(self.settings.cosmos_container)

    def get(self, codigo_partida: str) -> Partida:
        try:
            doc = self._container.read_item(item=codigo_partida, partition_key=codigo_partida)
        except exceptions.CosmosResourceNotFoundError as e:
            raise PartidaNoEncontrada(f"No existe partida con código '{codigo_partida}'") from e
        return Partida.model_validate(doc)

    def upsert(self, partida: Partida) -> Partida:
        doc = partida.model_dump(mode="json")
        self._container.upsert_item(doc)
        return partida

    def list_all(self) -> list[PartidaResumen]:
        query = """
            SELECT c.codigo_partida, c.personaje.nombre AS nombre_personaje,
                   c.metadata.turno_actual, c.metadata.estado,
                   c.metadata.genero, c.metadata.creada_en
            FROM c
            ORDER BY c.metadata.creada_en DESC
        """
        items = list(self._container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
        return [PartidaResumen(**item) for item in items]

    def exists(self, codigo_partida: str) -> bool:
        try:
            self._container.read_item(item=codigo_partida, partition_key=codigo_partida)
            return True
        except exceptions.CosmosResourceNotFoundError:
            return False
