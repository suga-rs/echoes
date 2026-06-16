"""Repositorio de usuarios en Cosmos DB."""

from azure.cosmos import CosmosClient, exceptions
from azure.cosmos.container import ContainerProxy
from azure.identity import DefaultAzureCredential

from app.core.config import Settings, get_settings
from app.core.exceptions import UsuarioYaExisteError
from app.core.logging import get_logger
from app.models.domain import Usuario

logger = get_logger("repo.usuarios")


class UsuarioRepository:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._container = self._build_container()

    def _build_container(self) -> ContainerProxy:
        if self.settings.cosmos_key:
            logger.info("Cosmos(usuarios): usando key")
            client = CosmosClient(self.settings.cosmos_endpoint, self.settings.cosmos_key)
        else:
            logger.info("Cosmos(usuarios): usando Entra ID")
            client = CosmosClient(
                self.settings.cosmos_endpoint, credential=DefaultAzureCredential()
            )
        db = client.get_database_client(self.settings.cosmos_database)
        return db.get_container_client(self.settings.cosmos_usuarios_container)

    def get(self, user_id: str) -> Usuario | None:
        try:
            doc = self._container.read_item(item=user_id, partition_key=user_id)
        except exceptions.CosmosResourceNotFoundError:
            return None
        return Usuario.model_validate(doc)

    def get_by_username(self, username_lower: str) -> Usuario | None:
        query = "SELECT * FROM c WHERE c.username_lower = @u"
        params: list[dict[str, object]] = [{"name": "@u", "value": username_lower}]
        items = list(
            self._container.query_items(
                query=query, parameters=params, enable_cross_partition_query=True
            )
        )
        if not items:
            return None
        return Usuario.model_validate(items[0])

    def create(self, usuario: Usuario) -> Usuario:
        """Inserta un usuario nuevo. Lanza UsuarioYaExisteError si ya existe
        (por id o por la unique key de username_lower del contenedor)."""
        doc = usuario.model_dump(mode="json")
        try:
            self._container.create_item(doc)
        except exceptions.CosmosResourceExistsError as e:
            raise UsuarioYaExisteError(
                f"Ya existe un usuario con username '{usuario.username}'"
            ) from e
        return usuario

    def upsert(self, usuario: Usuario) -> Usuario:
        self._container.upsert_item(usuario.model_dump(mode="json"))
        return usuario
