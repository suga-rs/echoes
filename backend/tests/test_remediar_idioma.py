"""Tests de la remediación de idioma one-off (scripts/remediar_idioma.py).

Hermético: el LLM y el repo se mockean; sin Azure ni red.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from app.models.domain import (
    NPC,
    Actitud,
    EstadoPartida,
    Genero,
    MetadataPartida,
    Partida,
    PartidaResumen,
    Personaje,
    TurnoHistorial,
    WorldState,
)
from scripts import remediar_idioma


def _partida_en_ingles() -> Partida:
    """Partida legacy con objetivo e inventario en inglés y estado rico para
    verificar que la remediación no toca nada más."""
    return Partida(
        id="abc",
        codigo_partida="abc",
        metadata=MetadataPartida(genero=Genero.FANTASIA, creada_en=datetime.now(UTC)),
        personaje=Personaje(
            nombre="Lyra",
            descripcion_narrativa="Arqueóloga escéptica.",
            descripcion_visual_en="Woman around 40, dark brown wavy hair, olive jacket.",
            inventario=["rusty key", "old map"],
        ),
        world_state=WorldState(
            ubicacion_actual="Cripta",
            objetivo="Find the heart of the mountain",
            npcs=[NPC(nombre="Eldrin", descripcion="Un ermitaño", actitud=Actitud.NEUTRAL)],
            resumen_historia="Resumen previo.",
        ),
        historial=[
            TurnoHistorial(
                turno=1,
                accion_jugador="mirar",
                narrativa="Ves la cripta.",
                opciones=["a", "b", "c"],
            )
        ],
    )


def _foundry_que_devuelve(textos: list[str]) -> MagicMock:
    foundry = MagicMock()
    foundry.chat_json.return_value = {"textos": textos}
    return foundry


# --- traducir_si_hace_falta --------------------------------------------------


def test_traducir_devuelve_mismo_largo_y_orden():
    foundry = _foundry_que_devuelve(["Hallar la montaña", "llave oxidada"])
    out = remediar_idioma.traducir_si_hace_falta(["Find the mountain", "rusty key"], foundry)
    assert out == ["Hallar la montaña", "llave oxidada"]


def test_traducir_lista_vacia_no_llama_al_llm():
    foundry = MagicMock()
    assert remediar_idioma.traducir_si_hace_falta([], foundry) == []
    foundry.chat_json.assert_not_called()


def test_traducir_falla_si_el_largo_no_coincide():
    foundry = _foundry_que_devuelve(["solo uno"])
    try:
        remediar_idioma.traducir_si_hace_falta(["a", "b"], foundry)
        raise AssertionError("esperaba ValueError")
    except ValueError:
        pass


# --- remediar_partida: 5.1 traduce, 5.2 idempotente, 5.3 preserva ------------


def test_remediar_traduce_objetivo_e_inventario_ingles():
    partida = _partida_en_ingles()
    foundry = _foundry_que_devuelve(
        ["Encontrar el corazón de la montaña", "llave oxidada", "mapa viejo"]
    )
    cambio = remediar_idioma.remediar_partida(partida, foundry)
    assert cambio is True
    assert partida.world_state.objetivo == "Encontrar el corazón de la montaña"
    assert partida.personaje.inventario == ["llave oxidada", "mapa viejo"]


def test_remediar_es_idempotente_cuando_ya_esta_en_espanol():
    partida = _partida_en_ingles()
    partida.world_state.objetivo = "Encontrar el corazón de la montaña"
    partida.personaje.inventario = ["llave oxidada", "mapa viejo"]
    # El LLM devuelve verbatim lo que ya está en español.
    foundry = _foundry_que_devuelve(
        ["Encontrar el corazón de la montaña", "llave oxidada", "mapa viejo"]
    )
    cambio = remediar_idioma.remediar_partida(partida, foundry)
    assert cambio is False
    assert partida.world_state.objetivo == "Encontrar el corazón de la montaña"
    assert partida.personaje.inventario == ["llave oxidada", "mapa viejo"]


def test_remediar_preserva_campos_en_historial_y_resto_del_estado():
    partida = _partida_en_ingles()
    foundry = _foundry_que_devuelve(
        ["Encontrar el corazón de la montaña", "llave oxidada", "mapa viejo"]
    )
    remediar_idioma.remediar_partida(partida, foundry)

    # Campos `_en`, historial, npcs, resumen y metadata intactos.
    assert partida.personaje.descripcion_visual_en.startswith("Woman around 40")
    assert partida.historial[0].narrativa == "Ves la cripta."
    assert partida.world_state.npcs[0].nombre == "Eldrin"
    assert partida.world_state.resumen_historia == "Resumen previo."
    assert partida.world_state.ubicacion_actual == "Cripta"


# --- main: persiste solo con --write ----------------------------------------


def _patch_main(monkeypatch, partida: Partida) -> MagicMock:
    repo = MagicMock()
    repo.list_all.return_value = [
        PartidaResumen(
            codigo_partida=partida.codigo_partida,
            nombre_personaje=partida.personaje.nombre,
            turno_actual=1,
            estado=EstadoPartida.EN_CURSO,
            genero=Genero.FANTASIA,
            creada_en=datetime.now(UTC),
        )
    ]
    repo.get.return_value = partida
    foundry = _foundry_que_devuelve(
        ["Encontrar el corazón de la montaña", "llave oxidada", "mapa viejo"]
    )
    monkeypatch.setattr(remediar_idioma, "PartidaRepository", lambda *a, **k: repo)
    monkeypatch.setattr(remediar_idioma, "FoundryClient", lambda *a, **k: foundry)
    return repo


def test_main_write_persiste_la_partida(monkeypatch):
    repo = _patch_main(monkeypatch, _partida_en_ingles())
    monkeypatch.setattr("sys.argv", ["remediar_idioma", "--write"])
    assert remediar_idioma.main() == 0
    repo.upsert.assert_called_once()


def test_main_dry_run_no_persiste(monkeypatch):
    repo = _patch_main(monkeypatch, _partida_en_ingles())
    monkeypatch.setattr("sys.argv", ["remediar_idioma"])
    assert remediar_idioma.main() == 0
    repo.upsert.assert_not_called()
