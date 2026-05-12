# Backend — Generador de Aventuras de Texto con IA

API REST construida con FastAPI que orquesta la generación de aventuras interactivas usando Microsoft Foundry (gpt-4.1-mini para narrativa, gpt-image-2 para imágenes) y persiste en Azure Cosmos DB.

## Estructura

```
backend/
├── app/
│   ├── api/              # endpoints HTTP
│   ├── services/         # lógica de negocio
│   ├── repositories/     # acceso a datos
│   ├── models/           # Pydantic + JSON schema
│   ├── core/             # config, logging, excepciones
│   └── main.py
├── scripts/
├── tests/
├── pyproject.toml
├── .env.example
└── .gitignore
```

## Quickstart

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env       # completar con valores reales
python scripts/verify_setup.py
uvicorn app.main:app --reload --port 8000
```

Docs interactivas: http://localhost:8000/docs

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/healthz` | Liveness probe |
| POST | `/api/partidas/start` | Crear nueva partida |
| POST | `/api/partidas/{codigo}/turn` | Avanzar un turno |
| GET | `/api/partidas/{codigo}/resume` | Recuperar estado completo |
| GET | `/api/partidas/{codigo}/state` | Resumen del world state |

## Tests

```bash
pytest tests/ -v
```

Los tests usan mocks de Foundry/Cosmos, no requieren credenciales reales.
