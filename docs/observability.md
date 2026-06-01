# Observabilidad

Echoes emite **logs estructurados (JSON)**, **trazas** y **métricas** vía OpenTelemetry. Cuando
`APPLICATIONINSIGHTS_CONNECTION_STRING` está seteada, `configure_azure_monitor`
([app/core/logging.py](../backend/app/core/logging.py)) exporta todo a **Azure Application
Insights**. Sin esa variable, OTel queda en no-op (seguro en dev/local).

## Qué se emite

**Logs estructurados** ([app/core/telemetry.py](../backend/app/core/telemetry.py), `JsonFormatter`):
cada línea es JSON con `timestamp, level, logger, message`, los campos extra del evento y
`trace_id`/`span_id` si hay un span activo. Controlado por `LOG_FORMAT` (`json` por defecto, `text`
para dev). Eventos clave:
- `llm_call`: `operation` (`chat`/`chat_stream`/`image`), `model`, `latency_ms`,
  `prompt_tokens`, `completion_tokens`, `total_tokens`, `finish_reason`.
- `turno_feedback`: `incoherente`.

**Trazas:** un span por turno (`avanzar_turno`, `crear_partida`, `avanzar_turno_stream`) con
atributos `codigo_partida`, `turno`, `genero`, `prompt_version`.

**Métricas:** `llm.tokens.total` (histograma), `llm.latency_ms` (histograma),
`llm.errors` (counter, attrs `operation`/`tipo`), `turno.feedback` (counter).

> Los **dashboards y alertas** se crean en el Azure Portal sobre estos datos. Esta es la
> definición de referencia (queries + umbrales); no se despliega desde el código.

## Queries KQL (Application Insights / Log Analytics)

Los `llm_call` llegan como `traces` con sus campos en `customDimensions`; las métricas como
`customMetrics`.

**Tokens por partida (top 20):**
```kusto
traces
| where message == "llm_call"
| extend codigo = tostring(customDimensions.codigo_partida),
         total = toint(customDimensions.total_tokens)
| where isnotnull(total)
| summarize tokens = sum(total) by codigo
| top 20 by tokens desc
```

**Latencia p95 por operación (última hora):**
```kusto
customMetrics
| where name == "llm.latency_ms" and timestamp > ago(1h)
| extend op = tostring(customDimensions.operation)
| summarize p95 = percentile(value, 95) by op
```

**Tasa de errores del LLM por tipo (por hora):**
```kusto
customMetrics
| where name == "llm.errors"
| extend tipo = tostring(customDimensions.tipo)
| summarize errores = sum(value) by tipo, bin(timestamp, 1h)
```

**Respuestas filtradas por Content Safety:**
```kusto
traces
| where message has "Content Safety" or message has "content_filter"
| summarize count() by bin(timestamp, 1h)
```

**Turnos marcados como incoherentes (feedback):**
```kusto
traces
| where message == "turno_feedback"
| where tostring(customDimensions.incoherente) == "True"
| summarize count() by bin(timestamp, 1d)
```

## Alertas sugeridas (Azure Monitor)

| Alerta | Condición | Severidad |
|---|---|---|
| Pico de errores LLM | `sum(llm.errors) > 5` en 5 min | 2 (alta) |
| Latencia degradada | `p95(llm.latency_ms) > 8000` ms en 15 min | 3 (media) |
| Consumo de tokens | `sum(llm.tokens.total) > <presupuesto>` por día | 3 (media) |
| Calidad cayendo | `turno_feedback(incoherente) > N` por día | 4 (baja) |

El feedback de incoherencia ([app/services/partida_service.py](../backend/app/services/partida_service.py),
`registrar_feedback`) es además el insumo para el futuro harness de evals (Fase 1 · item 8).
