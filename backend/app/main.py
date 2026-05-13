"""Entrypoint de FastAPI.

Levantar con:
    uvicorn app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import partidas
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import get_logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger = get_logger("startup")
    settings = get_settings()
    logger.info(
        "Backend iniciado. LLM=%s, Image=%s, EntraID=%s",
        settings.llm_deployment,
        settings.image_deployment,
        settings.use_entra_id,
    )
    yield
    logger.info("Backend cerrado")


app = FastAPI(
    title="Generador de Aventuras de Texto con IA",
    description="Backend que orquesta gpt-4.1-mini y gpt-image-2.",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger = get_logger("error")
    logger.warning("AppError en %s: %s", request.url.path, exc.mensaje)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "mensaje": exc.mensaje,
            "detalles": exc.detalles,
        },
    )


app.include_router(partidas.router)


@app.get("/healthz", tags=["health"])
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/", tags=["health"])
def root() -> dict:
    return {
        "name": "Generador de Aventuras de Texto con IA",
        "version": "0.1.0",
        "docs": "/docs",
    }
