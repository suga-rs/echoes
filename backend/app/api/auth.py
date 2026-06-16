"""Endpoints HTTP de autenticación."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_auth_service
from app.models.domain import AuthResponse, LoginRequest, RegisterRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    return service.register(body.username, body.password)


@router.post("/login", response_model=AuthResponse)
def login(
    body: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    return service.login(body.username, body.password)
