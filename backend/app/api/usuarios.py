"""Endpoints HTTP de perfil de usuario."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.dependencies import get_auth_service, get_current_user
from app.models.domain import AvatarResponse, PerfilResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])


@router.get("/me", response_model=PerfilResponse)
def get_perfil(
    service: Annotated[AuthService, Depends(get_auth_service)],
    user_id: Annotated[str, Depends(get_current_user)],
) -> PerfilResponse:
    return service.get_perfil(user_id)


@router.post("/me/avatar", response_model=AvatarResponse)
async def subir_avatar(
    service: Annotated[AuthService, Depends(get_auth_service)],
    user_id: Annotated[str, Depends(get_current_user)],
    file: Annotated[UploadFile, File(...)],
) -> AvatarResponse:
    contenido = await file.read()
    url = service.set_avatar(user_id, contenido, file.content_type or "")
    return AvatarResponse(avatar_url=url)
