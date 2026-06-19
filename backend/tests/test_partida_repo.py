"""Tests del PartidaRepository con el container de Cosmos mockeado."""

from unittest.mock import MagicMock, patch

from app.repositories.partida_repo import PartidaRepository


def _repo_con_container_mock(items: list[dict]) -> tuple[PartidaRepository, MagicMock]:
    container = MagicMock()
    container.query_items.return_value = iter(items)
    # CosmosClient autentica al construirse; evitamos tocar la red mockeando
    # la creación del container.
    with patch.object(PartidaRepository, "_build_container", return_value=container):
        repo = PartidaRepository()
    return repo, container


def _item(**extra) -> dict:
    base = {
        "codigo_partida": "abc-123",
        "nombre_personaje": "Lyra",
        "turno_actual": 2,
        "estado": "en_curso",
        "genero": "fantasía",
        "creada_en": "2026-06-16T00:00:00Z",
        "actualizada_en": None,
    }
    base.update(extra)
    return base


def test_list_all_selecciona_prompt_version_en_la_query():
    repo, container = _repo_con_container_mock([])
    repo.list_all()
    query = container.query_items.call_args.kwargs["query"]
    assert "prompt_version" in query


def test_list_all_expone_prompt_version_y_normaliza_legacy():
    repo, _ = _repo_con_container_mock(
        [
            _item(codigo_partida="con-version", prompt_version="2.1.0"),
            _item(codigo_partida="legacy"),  # sin prompt_version → 1.0.0
        ]
    )
    resultados = repo.list_all()
    por_codigo = {r.codigo_partida: r for r in resultados}
    assert por_codigo["con-version"].prompt_version == "2.1.0"
    assert por_codigo["legacy"].prompt_version == "1.0.0"
