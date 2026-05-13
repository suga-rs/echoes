# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Echoes** is an AI-powered interactive text adventure generator. Players choose a genre (fantasy, sci-fi, horror), describe their character, and the system narrates a branching story driven by `gpt-4.1-mini`, with procedural images from `gpt-image-2` via Azure Foundry. All game state is persisted in Azure Cosmos DB; images go to Azure Blob Storage.

## Commands

### Backend (run from `backend/`)

```bash
# Activate venv (Windows)
.venv\Scripts\activate

# Install (first time or after pyproject.toml changes)
pip install -e .[dev]

# Run dev server
fastapi dev app/main.py          # http://localhost:8000

# Tests
pytest                           # all tests
pytest tests/test_partida_service.py  # single file
pytest -k "test_crear"           # single test by name

# Lint / format
ruff check .
ruff format .
```

### Frontend (run from `frontend/`)

```bash
npm install                      # first time
npm run dev                      # http://localhost:3000
npm run build                    # production build
npm run lint                     # ESLint
npm run typecheck                # tsc --noEmit

# Regenerate API types from live backend (backend must be running on :8000)
npm run gen:types
```

## Architecture

### Backend — Layered

```
app/api/partidas.py          →  HTTP routes (FastAPI router, prefix /api/partidas)
app/services/partida_service.py  →  Orchestration: LLM calls, state mutation, image gen
app/repositories/partida_repo.py →  Cosmos DB CRUD
app/repositories/imagen_repo.py  →  Azure Blob Storage uploads
app/services/foundry_client.py   →  Azure OpenAI (chat + image generation)
app/services/prompts.py          →  System prompts and user-prompt builders
app/models/domain.py             →  All Pydantic domain models and DTOs
app/models/llm_schema.py         →  Strict JSON schemas for LLM responses + Pydantic wrappers
app/core/config.py               →  Settings via pydantic-settings (reads .env)
app/core/exceptions.py           →  AppError hierarchy (mapped to HTTP in main.py)
```

**LLM Contract:** The service injects `TURNO_JSON_SCHEMA` / `CREACION_JSON_SCHEMA` directly into the system prompt. The LLM must return JSON that validates against these schemas. `PartidaService._invocar_llm_con_reintento` does one automatic retry with the validation error fed back to the model before raising `RespuestaLLMInvalida`.

**Authentication:** Foundry client uses API key when `FOUNDRY_API_KEY` is set; falls back to `DefaultAzureCredential` (Entra ID) when it's empty.

**Settings:** `get_settings()` is `@lru_cache`'d. In tests, `conftest.py` sets env vars before import so no real Azure calls happen.

### Frontend — Single-Page, Zustand + React Query

```
src/app/page.tsx             →  Single route; top-level orchestration component
src/store/partida-store.ts   →  Zustand store (global game state)
src/lib/api.ts               →  HTTP client (one function per endpoint)
src/lib/types.ts             →  TypeScript types (kept in sync with backend OpenAPI)
src/components/              →  UI components (acciones, turno-card, inicio-dialog, etc.)
src/components/ui/           →  Primitive UI (Button, Dialog, Input — Radix + Tailwind)
```

**State hydration pattern:** Zustand persists only `codigoPartida` to `localStorage`. On reload, `page.tsx` detects `codigoPartida !== null && historial.length === 0` and calls `/resume` to re-hydrate all game state from the backend. If the backend returns an error (stale code), the store is reset.

**API base URL:** Read from `NEXT_PUBLIC_API_URL` env var; defaults to `http://localhost:8000`.

## Key Env Vars

| Var | Description |
|-----|-------------|
| `FOUNDRY_ENDPOINT` | Azure Foundry endpoint URL |
| `FOUNDRY_API_KEY` | Leave empty to use Entra ID instead |
| `LLM_DEPLOYMENT` | Model deployment name (e.g. `gpt-4.1-mini`) |
| `IMAGE_DEPLOYMENT` | Image model deployment (e.g. `gpt-image-2`) |
| `COSMOS_ENDPOINT` | Cosmos DB account URI |
| `COSMOS_KEY` | Cosmos DB key (empty = Entra ID) |
| `STORAGE_ACCOUNT_NAME` | Blob storage account name |
| `STORAGE_CONNECTION_STRING` | Blob connection string |
| `MAX_TURNOS_POR_PARTIDA` | Default 25 |
| `MAX_IMAGENES_POR_PARTIDA` | Default 5 |

Copy `backend/.env.example` → `backend/.env` and `frontend/.env.local.example` → `frontend/.env.local` to configure locally.
