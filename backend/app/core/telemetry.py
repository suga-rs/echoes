"""Telemetría de la capa LLM: logging estructurado + métricas/trazas OpenTelemetry.

Sin dependencias nuevas: usa logging stdlib y la API de OpenTelemetry ya presente
(vía azure-monitor-opentelemetry). Si no hay providers configurados, OTel devuelve
no-ops, así que todo es seguro de llamar sin Azure.

Para no introducir un import circular con app.core.logging, este módulo usa
logging.getLogger directamente.
"""

import functools
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from opentelemetry import metrics, trace

logger = logging.getLogger("app.telemetry")

_INSTRUMENTATION_NAME = "echoes.backend"

# Atributos estándar de un LogRecord: todo lo que NO esté acá es un campo "extra".
_STD_LOGRECORD_ATTRS = set(logging.makeLogRecord({}).__dict__.keys()) | {
    "message",
    "asctime",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    """Serializa cada registro a una línea JSON con sus campos extra y, si hay un
    span OTel activo, trace_id/span_id (para correlacionar logs ↔ trazas)."""

    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key not in _STD_LOGRECORD_ATTRS and not key.startswith("_"):
                data[key] = value

        if record.exc_info:
            data["exc_info"] = self.formatException(record.exc_info)

        ctx = trace.get_current_span().get_span_context()
        if ctx.is_valid:
            data["trace_id"] = format(ctx.trace_id, "032x")
            data["span_id"] = format(ctx.span_id, "016x")

        return json.dumps(data, ensure_ascii=False, default=str)


def log_event(log: logging.Logger, event: str, **fields: Any) -> None:
    """Emite un log estructurado: un nombre de evento + campos arbitrarios."""
    log.info(event, extra={"event": event, **fields})


# --- OpenTelemetry: tracer + métricas (lazy, cacheadas) ---


def get_tracer() -> trace.Tracer:
    return trace.get_tracer(_INSTRUMENTATION_NAME)


def traced(name: str) -> Callable:
    """Decorador para funciones sincrónicas: las ejecuta dentro de un span."""

    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with get_tracer().start_as_current_span(name):
                return fn(*args, **kwargs)

        return wrapper

    return deco


def add_span_attributes(**attrs: Any) -> None:
    """Setea atributos en el span activo (ignora valores None)."""
    span = trace.get_current_span()
    for key, value in attrs.items():
        if value is not None:
            span.set_attribute(key, value)


@lru_cache(maxsize=1)
def _instruments() -> dict[str, Any]:
    meter = metrics.get_meter(_INSTRUMENTATION_NAME)
    return {
        "tokens": meter.create_histogram(
            "llm.tokens.total", unit="token", description="Tokens totales por llamada LLM"
        ),
        "latency": meter.create_histogram(
            "llm.latency_ms", unit="ms", description="Latencia por llamada LLM"
        ),
        "errors": meter.create_counter("llm.errors", description="Errores de la capa LLM"),
        "feedback": meter.create_counter(
            "turno.feedback", description="Feedback de calidad por turno"
        ),
    }


def record_llm_call(
    *,
    operation: str,
    model: str,
    latency_ms: float,
    usage: Any | None = None,
    finish_reason: str | None = None,
    codigo_partida: str | None = None,
) -> None:
    """Registra una llamada al LLM como log estructurado + métricas de tokens/latencia."""
    prompt_tokens = getattr(usage, "prompt_tokens", None)
    completion_tokens = getattr(usage, "completion_tokens", None)
    total_tokens = getattr(usage, "total_tokens", None)

    log_event(
        logger,
        "llm_call",
        operation=operation,
        model=model,
        latency_ms=round(latency_ms, 1),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        finish_reason=finish_reason,
        codigo_partida=codigo_partida,
    )

    attrs = {"operation": operation, "model": model}
    inst = _instruments()
    inst["latency"].record(latency_ms, attrs)
    if isinstance(total_tokens, int | float):
        inst["tokens"].record(total_tokens, attrs)


def record_llm_error(*, operation: str, tipo: str) -> None:
    """Incrementa el counter de errores de la capa LLM."""
    _instruments()["errors"].add(1, {"operation": operation, "tipo": tipo})


def record_feedback(*, incoherente: bool) -> None:
    """Registra feedback de calidad de un turno (log + métrica)."""
    log_event(logger, "turno_feedback", incoherente=incoherente)
    _instruments()["feedback"].add(1, {"incoherente": str(incoherente).lower()})
