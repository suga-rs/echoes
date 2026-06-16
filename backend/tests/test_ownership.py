"""Tests de propiedad (ownership) de partidas por user_id."""

from factories import fake_creacion_llm_response

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
