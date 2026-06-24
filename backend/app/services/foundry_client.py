"""Cliente de Microsoft Foundry."""

import base64
import json
import random
import time
from collections.abc import AsyncGenerator, Callable
from typing import Any, Literal, TypeVar

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncAzureOpenAI,
    AzureOpenAI,
    InternalServerError,
    RateLimitError,
)

from app.core import telemetry
from app.core.config import Settings, get_settings
from app.core.exceptions import FoundryError
from app.core.logging import get_logger

logger = get_logger("foundry")

_T = TypeVar("_T")

# Errores que sí conviene reintentar (transitorios). El resto (BadRequestError,
# autenticación, content-filter) se re-lanza de inmediato sin reintento.
_TRANSITORIOS = (APIConnectionError, APITimeoutError, RateLimitError, InternalServerError)


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

    def _with_retries(self, fn: Callable[[], _T]) -> _T:
        """Ejecuta `fn`, reintentando con backoff exponencial + jitter solo ante
        errores transitorios. Otros errores se propagan de inmediato."""
        intentos = self.settings.llm_max_retries + 1
        ultimo: Exception | None = None
        for intento in range(intentos):
            try:
                return fn()
            except _TRANSITORIOS as e:
                ultimo = e
                if intento < intentos - 1:
                    delay = self.settings.llm_retry_base_delay * (2**intento)
                    delay += random.uniform(0, delay * 0.1)  # jitter
                    logger.warning(
                        "Foundry: error transitorio %s, reintento %s/%s en %.2fs",
                        type(e).__name__,
                        intento + 1,
                        intentos - 1,
                        delay,
                    )
                    time.sleep(delay)
        assert ultimo is not None  # solo se llega acá tras agotar reintentos
        logger.warning("Foundry: agotados los reintentos (%s)", intentos)
        raise ultimo

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.8,
        max_tokens: int = 1500,
    ) -> dict[str, Any]:
        t0 = time.perf_counter()
        try:
            response = self._with_retries(
                lambda: self._client.chat.completions.create(
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
            )
        except Exception as e:
            telemetry.record_llm_error(operation="chat", tipo=type(e).__name__)
            logger.exception("Foundry chat error")
            raise FoundryError(f"Error llamando al LLM: {e}") from e

        telemetry.record_llm_call(
            operation="chat",
            model=self.settings.llm_deployment,
            latency_ms=(time.perf_counter() - t0) * 1000,
            usage=getattr(response, "usage", None),
            finish_reason=response.choices[0].finish_reason,
        )

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
        t0 = time.perf_counter()
        try:
            response = self._with_retries(
                lambda: self._client.chat.completions.create(
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
            )
        except Exception as e:
            telemetry.record_llm_error(operation="chat", tipo=type(e).__name__)
            logger.exception("Foundry chat error")
            raise FoundryError(f"Error llamando al LLM: {e}") from e

        telemetry.record_llm_call(
            operation="chat",
            model=self.settings.llm_deployment,
            latency_ms=(time.perf_counter() - t0) * 1000,
            usage=getattr(response, "usage", None),
            finish_reason=response.choices[0].finish_reason,
        )

        content = response.choices[0].message.content or ""
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = None
        return content, parsed

    def generar_imagen(
        self,
        prompt: str,
        size: str = "1536x1024",
        *,
        output_format: Literal["jpeg", "png"] = "jpeg",
    ) -> bytes:
        t0 = time.perf_counter()
        # output_compression solo aplica a formatos con pérdida (jpeg). En PNG la
        # salida es sin pérdida: lo usamos para la referencia canónica del
        # personaje para no apilar una segunda compresión al re-inyectarla en
        # images.edit (evita la doble pérdida JPEG en cada escena).
        params: dict = dict(
            model=self.settings.image_deployment,
            prompt=prompt,
            size=size,
            n=1,
            quality="medium",
            output_format=output_format,
        )
        if output_format == "jpeg":
            params["output_compression"] = 80
        try:
            response = self._with_retries(lambda: self._client.images.generate(**params))
        except Exception as e:
            telemetry.record_llm_error(operation="image", tipo=type(e).__name__)
            logger.exception("Foundry image error")
            raise FoundryError(f"Error generando imagen: {e}") from e

        telemetry.record_llm_call(
            operation="image",
            model=self.settings.image_deployment,
            latency_ms=(time.perf_counter() - t0) * 1000,
            usage=getattr(response, "usage", None),
        )

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

    def editar_imagen(
        self,
        prompt: str,
        reference_bytes: bytes,
        *,
        size: str = "1536x1024",
        input_fidelity: Literal["high", "low"] = "high",
    ) -> bytes:
        """Genera una imagen de escena anclada a una imagen de referencia del
        personaje vía images.edit. input_fidelity="high" preserva la identidad
        (cara/atuendo) de la referencia."""
        t0 = time.perf_counter()
        # Etiquetar la referencia con su tipo real: las partidas nuevas la
        # almacenan en PNG sin pérdida, pero las viejas pueden tener un JPEG.
        if reference_bytes.startswith(b"\x89PNG"):
            ref_name, ref_mime = "reference.png", "image/png"
        else:
            ref_name, ref_mime = "reference.jpg", "image/jpeg"
        try:
            response = self._with_retries(
                lambda: self._client.images.edit(
                    model=self.settings.image_deployment,
                    image=(ref_name, reference_bytes, ref_mime),
                    prompt=prompt,
                    size=size,
                    n=1,
                    input_fidelity=input_fidelity,
                    quality="medium",
                    output_format="jpeg",
                    output_compression=80,
                )
            )
        except Exception as e:
            telemetry.record_llm_error(operation="image_edit", tipo=type(e).__name__)
            logger.exception("Foundry image edit error")
            raise FoundryError(f"Error editando imagen: {e}") from e

        telemetry.record_llm_call(
            operation="image_edit",
            model=self.settings.image_deployment,
            latency_ms=(time.perf_counter() - t0) * 1000,
            usage=getattr(response, "usage", None),
        )

        if not response.data:
            raise FoundryError("Respuesta de imagen (edit) vacía")

        item = response.data[0]
        b64 = getattr(item, "b64_json", None)
        if b64:
            return base64.b64decode(b64)

        url = getattr(item, "url", None)
        if url:
            raise FoundryError("Imagen (edit) devuelta como URL; configurar para b64_json")

        raise FoundryError("Imagen (edit) no contiene datos reconocibles")

    async def chat_streaming_async(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.8,
        max_tokens: int = 1500,
    ) -> AsyncGenerator[str, None]:
        """Streams raw LLM text chunks (JSON tokens) as they arrive."""
        # Nota: el backoff de _with_retries es sync; el inicio del stream no se
        # reintenta. Un error transitorio acá emerge como FoundryError sin reintento.
        t0 = time.perf_counter()
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
                stream_options={"include_usage": True},
            )
        except Exception as e:
            telemetry.record_llm_error(operation="chat_stream", tipo=type(e).__name__)
            logger.exception("Foundry streaming error")
            raise FoundryError(f"Error iniciando stream LLM: {e}") from e

        usage = None
        finish_reason = None
        async with stream:
            async for chunk in stream:
                if not chunk.choices:
                    # El chunk final de usage llega con choices vacío.
                    usage = getattr(chunk, "usage", None) or usage
                    continue
                if chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason
                content = chunk.choices[0].delta.content
                if content:
                    yield content

        telemetry.record_llm_call(
            operation="chat_stream",
            model=self.settings.llm_deployment,
            latency_ms=(time.perf_counter() - t0) * 1000,
            usage=usage,
            finish_reason=finish_reason,
        )
