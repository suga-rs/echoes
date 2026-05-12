"""Configuración de la aplicación. Lee desde variables de entorno (.env en dev)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración global de la aplicación."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Foundry / OpenAI
    foundry_endpoint: str = Field(...)
    foundry_api_key: str = Field(default="")
    llm_deployment: str = Field(...)
    image_deployment: str = Field(...)
    api_version: str = Field(default="2025-04-01-preview")

    # Cosmos DB
    cosmos_endpoint: str = Field(...)
    cosmos_key: str = Field(default="")
    cosmos_database: str = Field(default="aventuras")
    cosmos_container: str = Field(default="partidas")

    # Blob Storage
    storage_account_name: str = Field(...)
    storage_container: str = Field(default="imagenes-aventuras")
    storage_connection_string: str = Field(default="")

    # Observability
    applicationinsights_connection_string: str = Field(default="")

    # App config
    log_level: str = Field(default="INFO")
    max_turnos_por_partida: int = Field(default=25)
    max_imagenes_por_partida: int = Field(default=5)
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:5173")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def use_entra_id(self) -> bool:
        return not self.foundry_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
