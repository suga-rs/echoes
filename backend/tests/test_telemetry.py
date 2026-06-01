"""Tests de la capa de telemetría: JsonFormatter, record_llm_call y métricas OTel.

Las métricas/trazas se verifican con exporters in-memory configurados en conftest.
"""

import json
import logging
from types import SimpleNamespace

from opentelemetry import trace

from app.core import telemetry


def _collect_metrics(reader) -> dict[str, list]:
    data = reader.get_metrics_data()
    out: dict[str, list] = {}
    if not data:
        return out
    for rm in data.resource_metrics:
        for sm in rm.scope_metrics:
            for metric in sm.metrics:
                out.setdefault(metric.name, []).extend(metric.data.data_points)
    return out


def _make_record(msg: str = "msg", args: tuple = (), extra: dict | None = None):
    logger = logging.getLogger("app.test")
    return logger.makeRecord("app.test", logging.INFO, "f", 1, msg, args, None, extra=extra)


def test_json_formatter_incluye_mensaje_nivel_y_campos_extra():
    formatter = telemetry.JsonFormatter()
    record = _make_record("hola %s", ("mundo",), {"event": "llm_call", "tokens": 5})

    out = json.loads(formatter.format(record))

    assert out["message"] == "hola mundo"
    assert out["level"] == "INFO"
    assert out["logger"] == "app.test"
    assert out["event"] == "llm_call"
    assert out["tokens"] == 5


def test_json_formatter_sin_span_no_incluye_trace_id():
    out = json.loads(telemetry.JsonFormatter().format(_make_record()))
    assert "trace_id" not in out


def test_json_formatter_incluye_trace_id_dentro_de_span(span_exporter):
    tracer = trace.get_tracer("test")
    formatter = telemetry.JsonFormatter()

    with tracer.start_as_current_span("op"):
        out = json.loads(formatter.format(_make_record()))

    assert len(out["trace_id"]) == 32
    assert len(out["span_id"]) == 16


def test_record_llm_call_emite_log_estructurado_y_metricas(metric_reader, caplog):
    usage = SimpleNamespace(prompt_tokens=100, completion_tokens=50, total_tokens=150)

    with caplog.at_level(logging.INFO, logger="app.telemetry"):
        telemetry.record_llm_call(
            operation="chat",
            model="test-model",
            latency_ms=12.3,
            usage=usage,
            finish_reason="stop",
        )

    rec = next(r for r in caplog.records if getattr(r, "event", None) == "llm_call")
    assert rec.total_tokens == 150
    assert rec.operation == "chat"
    assert rec.model == "test-model"

    metrics_by_name = _collect_metrics(metric_reader)
    assert "llm.latency_ms" in metrics_by_name
    token_points = [
        p for p in metrics_by_name["llm.tokens.total"] if p.attributes.get("model") == "test-model"
    ]
    assert token_points and token_points[0].sum == 150


def test_record_llm_error_incrementa_counter(metric_reader):
    telemetry.record_llm_error(operation="chat", tipo="APITimeoutError")

    points = _collect_metrics(metric_reader).get("llm.errors", [])
    tipo_points = [p for p in points if p.attributes.get("tipo") == "APITimeoutError"]
    assert tipo_points and tipo_points[0].value >= 1
