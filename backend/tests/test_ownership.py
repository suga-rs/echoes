"""Tests de propiedad (ownership) de partidas por user_id."""

import pytest
from factories import fake_creacion_llm_response

from app.core.exceptions import AccesoDenegadoError, PartidaNoEncontradaError
from app.models.domain import Genero
from app.services.partida_service import PartidaService


def _svc(foundry_mock, partida_repo_mock, imagen_repo_mock) -> PartidaService:
    foundry_mock.chat_json_raw.return_value = ("{}", fake_creacion_llm_response())
    foundry_mock.generar_imagen.return_value = b"\x89PNG" + b"\x00" * 100
    imagen_repo_mock.subir_imagen.return_value = "https://fake.blob/x.png"
    return PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )


def test_start_autenticado_estampa_user_id(foundry_mock, partida_repo_mock, imagen_repo_mock):
    svc = _svc(foundry_mock, partida_repo_mock, imagen_repo_mock)
    svc.crear_partida(Genero.FANTASIA, "una arqueóloga escéptica", owner_id="user-7")

    guardada = partida_repo_mock.upsert.call_args[0][0]
    assert guardada.metadata.user_id == "user-7"


def test_start_anonimo_estampa_creator(foundry_mock, partida_repo_mock, imagen_repo_mock):
    svc = _svc(foundry_mock, partida_repo_mock, imagen_repo_mock)
    svc.crear_partida(Genero.FANTASIA, "una arqueóloga escéptica")  # sin owner_id

    guardada = partida_repo_mock.upsert.call_args[0][0]
    assert guardada.metadata.user_id == "0"


def test_listar_partidas_pasa_user_id(foundry_mock, partida_repo_mock, imagen_repo_mock):
    partida_repo_mock.list_all.return_value = []
    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    svc.listar_partidas(user_id="user-7")
    partida_repo_mock.list_all.assert_called_once_with(user_id="user-7")


def test_resume_por_codigo_no_requiere_auth(
    foundry_mock, partida_repo_mock, imagen_repo_mock, partida_de_ejemplo
):
    partida_repo_mock.get.return_value = partida_de_ejemplo
    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    # get_partida no recibe identidad: jugar por código sigue abierto.
    p = svc.get_partida("test-abc-123")
    assert p.codigo_partida == "test-abc-123"


def _svc_plano(foundry_mock, partida_repo_mock, imagen_repo_mock) -> PartidaService:
    return PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )


def test_eliminar_partida_owner_borra_doc_y_blobs(
    foundry_mock, partida_repo_mock, imagen_repo_mock, partida_de_ejemplo
):
    partida_de_ejemplo.metadata.user_id = "user-7"
    partida_repo_mock.get.return_value = partida_de_ejemplo
    svc = _svc_plano(foundry_mock, partida_repo_mock, imagen_repo_mock)

    svc.eliminar_partida("test-abc-123", "user-7")

    imagen_repo_mock.eliminar_imagenes.assert_called_once_with("test-abc-123")
    partida_repo_mock.delete.assert_called_once_with("test-abc-123")


def test_eliminar_partida_bucket_creator_prohibido(
    foundry_mock, partida_repo_mock, imagen_repo_mock, partida_de_ejemplo
):
    partida_de_ejemplo.metadata.user_id = "0"
    partida_repo_mock.get.return_value = partida_de_ejemplo
    svc = _svc_plano(foundry_mock, partida_repo_mock, imagen_repo_mock)

    with pytest.raises(AccesoDenegadoError):
        svc.eliminar_partida("test-abc-123", "user-7")

    partida_repo_mock.delete.assert_not_called()
    imagen_repo_mock.eliminar_imagenes.assert_not_called()


def test_eliminar_partida_no_owner_prohibido(
    foundry_mock, partida_repo_mock, imagen_repo_mock, partida_de_ejemplo
):
    partida_de_ejemplo.metadata.user_id = "user-7"
    partida_repo_mock.get.return_value = partida_de_ejemplo
    svc = _svc_plano(foundry_mock, partida_repo_mock, imagen_repo_mock)

    with pytest.raises(AccesoDenegadoError):
        svc.eliminar_partida("test-abc-123", "otro-user")

    partida_repo_mock.delete.assert_not_called()
    imagen_repo_mock.eliminar_imagenes.assert_not_called()


def test_eliminar_partida_inexistente_404(foundry_mock, partida_repo_mock, imagen_repo_mock):
    partida_repo_mock.get.side_effect = PartidaNoEncontradaError("no existe")
    svc = _svc_plano(foundry_mock, partida_repo_mock, imagen_repo_mock)

    with pytest.raises(PartidaNoEncontradaError):
        svc.eliminar_partida("missing", "user-7")

    partida_repo_mock.delete.assert_not_called()
