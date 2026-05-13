"""Cliente de Microsoft Foundry."""

import base64
import json
from collections.abc import AsyncGenerator
from typing import Any

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI, AzureOpenAI

from app.core.config import Settings, get_settings
from app.core.exceptions import FoundryError
from app.core.logging import get_logger

logger = get_logger("foundry")


class FoundryClient:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._client = self._build_client()
        self._async_client = self._build_async_client()

    def _build_client(self) -> AzureOpenAI:
        if self.settings.use_entra_id:
            logger.info("Foundry: usando Entra ID")
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://cognitiveservices.azure.com/.default",
            )
            return AzureOpenAI(
                azure_endpoint=self.settings.foundry_endpoint,
                azure_ad_token_provider=token_provider,
                api_version=self.settings.api_version,
            )
        return AzureOpenAI(
            azure_endpoint=self.settings.foundry_endpoint,
            api_key=self.settings.foundry_api_key,
            api_version=self.settings.api_version,
        )

    def _build_async_client(self) -> AsyncAzureOpenAI:
        if self.settings.use_entra_id:
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://cognitiveservices.azure.com/.default",
            )
            return AsyncAzureOpenAI(
                azure_endpoint=self.settings.foundry_endpoint,
                azure_ad_token_provider=token_provider,
                api_version=self.settings.api_version,
            )
        return AsyncAzureOpenAI(
            azure_endpoint=self.settings.foundry_endpoint,
            api_key=self.settings.foundry_api_key,
            api_version=self.settings.api_version,
        )

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.8,
        max_tokens: int = 1500,
    ) -> dict[str, Any]:
        try:
            response = self._client.chat.completions.create(
                model=self.settings.llm_deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=temperature,
                top_p=0.95,
                max_tokens=max_tokens,
                frequency_penalty=0.3,
                presence_penalty=0.1,
            )
        except Exception as e:
            logger.exception("Foundry chat error")
            raise FoundryError(f"Error llamando al LLM: {e}") from e

        content = response.choices[0].message.content
        if not content:
            raise FoundryError("LLM devolvió respuesta vacía")

        if response.choices[0].finish_reason == "content_filter":
            raise FoundryError("Respuesta filtrada por Content Safety")

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise FoundryError(f"JSON malformado: {e}") from e

    def chat_json_raw(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.8,
        max_tokens: int = 1500,
    ) -> tuple[str, dict[str, Any] | None]:
        try:
            response = self._client.chat.completions.create(
                model=self.settings.llm_deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=temperature,
                top_p=0.95,
                max_tokens=max_tokens,
                frequency_penalty=0.3,
                presence_penalty=0.1,
            )
        except Exception as e:
            logger.exception("Foundry chat error")
            raise FoundryError(f"Error llamando al LLM: {e}") from e

        content = response.choices[0].message.content or ""
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = None
        return content, parsed

    def generar_imagen(self, prompt: str, size: str = "1536x1024") -> bytes:
        try:
            response = self._client.images.generate(
                model=self.settings.image_deployment,
                prompt=prompt,
                size=size,
                n=1,
                quality="low",
                output_format="jpeg",
                output_compression=80,
            )
        except Exception as e:
            logger.exception("Foundry image error")
            raise FoundryError(f"Error generando imagen: {e}") from e

        if not response.data:
            raise FoundryError("Respuesta de imagen vacía")

        item = response.data[0]
        b64 = getattr(item, "b64_json", None)
        if b64:
            return base64.b64decode(b64)

        url = getattr(item, "url", None)
        if url:
            raise FoundryError("Imagen devuelta como URL; configurar para b64_json")

        raise FoundryError("Imagen no contiene datos reconocibles")

    async def chat_streaming_async(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.8,
        max_tokens: int = 1500,
    ) -> AsyncGenerator[str, None]:
        """Streams raw LLM text chunks (JSON tokens) as they arrive."""
        try:
            stream = await self._async_client.chat.completions.create(
                model=self.settings.llm_deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=temperature,
                top_p=0.95,
                max_tokens=max_tokens,
                frequency_penalty=0.3,
                presence_penalty=0.1,
                stream=True,
            )
        except Exception as e:
            logger.exception("Foundry streaming error")
            raise FoundryError(f"Error iniciando stream LLM: {e}") from e

        async with stream:
            async for chunk in stream:
                if not chunk.choices:
                    continue
                content = chunk.choices[0].delta.content
                if content:
                    yield content
