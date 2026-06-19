"""Tests de contrato de los schemas JSON del LLM (regresión).

Protegen TURNO_JSON_SCHEMA y CREACION_JSON_SCHEMA ante cambios de prompt/modelo.
Parten de un payload válido (builders de factories.py) y lo mutan a casos inválidos.
Pura validación de datos: sin Azure, sin red.
"""

import copy
from typing import Any

import pytest
from factories import fake_creacion_llm_response, fake_turno_llm_response
from jsonschema import ValidationError, validate

from app.models.llm_schema import (
    CREACION_JSON_SCHEMA,
    TURNO_JSON_SCHEMA,
    CreacionLLMResponse,
    TurnoLLMResponse,
)


def _con(base: dict, path: list[str], value: Any) -> dict:
    """Copia de `base` con la clave en `path` seteada a `value`."""
    d = copy.deepcopy(base)
    ref = d
    for key in path[:-1]:
        ref = ref[key]
    ref[path[-1]] = value
    return d


def _sin(base: dict, path: list[str]) -> dict:
    """Copia de `base` sin la clave en `path`."""
    d = copy.deepcopy(base)
    ref = d
    for key in path[:-1]:
        ref = ref[key]
    del ref[path[-1]]
    return d


# --------------------------------------------------------------------------- TURNO


def test_turno_baseline_valido():
    payload = fake_turno_llm_response()
    validate(payload, TURNO_JSON_SCHEMA)  # no debe lanzar
    modelo = TurnoLLMResponse.model_validate(payload)
    assert len(modelo.opciones) == 3
    assert modelo.estado_aventura.tipo == "en_curso"


def test_turno_guard_descripcion_escena_es_str_requerido():
    """Regresión Fase 0: descripcion_escena_en pasó de `str | None` a `str` requerido."""
    # El schema lo exige: quitarlo debe fallar.
    with pytest.raises(ValidationError):
        validate(
            _sin(fake_turno_llm_response(), ["generar_imagen", "descripcion_escena_en"]),
            TURNO_JSON_SCHEMA,
        )
    # Y el modelo Pydantic lo expone siempre como str.
    modelo = TurnoLLMResponse.model_validate(fake_turno_llm_response())
    assert isinstance(modelo.generar_imagen.descripcion_escena_en, str)


_NPC_VALIDO = {"nombre": "Eldrin", "descripcion": "Un ermitaño", "actitud": "neutral"}

TURNO_INVALIDOS = [
    pytest.param(_con(fake_turno_llm_response(), ["narrativa"], "x" * 49), id="narrativa-corta"),
    pytest.param(_con(fake_turno_llm_response(), ["narrativa"], "x" * 1501), id="narrativa-larga"),
    pytest.param(_con(fake_turno_llm_response(), ["opciones"], ["aaa", "bbb"]), id="dos-opciones"),
    pytest.param(
        _con(fake_turno_llm_response(), ["opciones"], ["aaa", "bbb", "ccc", "ddd"]),
        id="cuatro-opciones",
    ),
    pytest.param(
        _con(fake_turno_llm_response(), ["opciones"], ["ab", "bbb", "ccc"]), id="opcion-corta"
    ),
    pytest.param(
        _con(fake_turno_llm_response(), ["opciones"], ["x" * 101, "bbb", "ccc"]), id="opcion-larga"
    ),
    pytest.param(
        _sin(fake_turno_llm_response(), ["actualizaciones_estado", "ubicacion_nueva"]),
        id="estado-falta-clave",
    ),
    pytest.param(
        _con(fake_turno_llm_response(), ["actualizaciones_estado", "foo"], "bar"),
        id="estado-clave-extra",
    ),
    pytest.param(
        _con(
            fake_turno_llm_response(),
            ["actualizaciones_estado", "npc_encontrado"],
            {**_NPC_VALIDO, "actitud": "enojada"},
        ),
        id="npc-actitud-invalida",
    ),
    pytest.param(
        _con(
            fake_turno_llm_response(),
            ["actualizaciones_estado", "npc_actitud_cambio"],
            {"nombre": "Eldrin", "nueva_actitud": "furiosa"},
        ),
        id="npc-cambio-invalido",
    ),
    pytest.param(
        _con(fake_turno_llm_response(), ["estado_aventura", "tipo"], "pausada"), id="tipo-invalido"
    ),
    pytest.param(
        _con(fake_turno_llm_response(), ["estado_aventura", "final"], "victoria"),
        id="final-invalido",
    ),
    pytest.param(
        _sin(fake_turno_llm_response(), ["generar_imagen", "necesaria"]),
        id="imagen-falta-necesaria",
    ),
    pytest.param(
        _con(fake_turno_llm_response(), ["generar_imagen", "necesaria"], "yes"),
        id="necesaria-no-bool",
    ),
    pytest.param(_con(fake_turno_llm_response(), ["foo"], "bar"), id="clave-extra-raiz"),
    pytest.param(_sin(fake_turno_llm_response(), ["arco"]), id="falta-arco"),
    pytest.param(_sin(fake_turno_llm_response(), ["resumen_historia"]), id="falta-resumen"),
    pytest.param(
        _con(fake_turno_llm_response(), ["arco", "fase_narrativa"], "epilogo"),
        id="fase-invalida",
    ),
    pytest.param(
        _con(fake_turno_llm_response(), ["arco", "tension"], 11), id="tension-fuera-de-rango"
    ),
]


@pytest.mark.parametrize("payload", TURNO_INVALIDOS)
def test_turno_invalido_falla(payload: dict):
    with pytest.raises(ValidationError):
        validate(payload, TURNO_JSON_SCHEMA)


# --------------------------------------------------------------------------- CREACION


def test_creacion_baseline_valido():
    payload = fake_creacion_llm_response()
    validate(payload, CREACION_JSON_SCHEMA)  # no debe lanzar
    modelo = CreacionLLMResponse.model_validate(payload)
    assert modelo.personaje.nombre == "Lyra"
    assert len(modelo.primera_escena.opciones) == 3


CREACION_INVALIDOS = [
    pytest.param(_sin(fake_creacion_llm_response(), ["personaje", "nombre"]), id="falta-nombre"),
    pytest.param(
        _con(fake_creacion_llm_response(), ["personaje", "foo"], "x"), id="personaje-clave-extra"
    ),
    pytest.param(
        _con(
            fake_creacion_llm_response(),
            ["personaje", "inventario_inicial"],
            ["a", "b", "c", "d", "e", "f"],
        ),
        id="inventario-excede-5",
    ),
    pytest.param(
        _con(fake_creacion_llm_response(), ["primera_escena", "opciones"], ["a", "b"]),
        id="opciones-no-tres",
    ),
    pytest.param(
        _con(fake_creacion_llm_response(), ["personaje", "nombre"], "x" * 51), id="nombre-largo"
    ),
    pytest.param(
        _con(fake_creacion_llm_response(), ["personaje", "descripcion_visual_en"], "corto"),
        id="visual-corta",
    ),
    pytest.param(_con(fake_creacion_llm_response(), ["foo"], "bar"), id="clave-extra-raiz"),
]


@pytest.mark.parametrize("payload", CREACION_INVALIDOS)
def test_creacion_invalido_falla(payload: dict):
    with pytest.raises(ValidationError):
        validate(payload, CREACION_JSON_SCHEMA)


# ----------------------------------------------------------- IDIOMA POR CAMPO


def _es_descr_espanol(node: dict) -> bool:
    return "español rioplatense" in node.get("description", "").lower()


def test_campos_que_fugaban_llevan_description_en_espanol():
    """Las properties cortas tipo etiqueta que fugaban al inglés
    (objetivo, inventario, opciones) deben declarar su idioma en el schema,
    reforzando la regla del system prompt donde el modelo emite cada valor."""
    turno_props = TURNO_JSON_SCHEMA["properties"]
    estado_props = turno_props["actualizaciones_estado"]["properties"]
    assert _es_descr_espanol(turno_props["opciones"]["items"])
    assert _es_descr_espanol(estado_props["agregar_inventario"]["items"])
    assert _es_descr_espanol(estado_props["quitar_inventario"]["items"])

    creacion_props = CREACION_JSON_SCHEMA["properties"]
    assert _es_descr_espanol(creacion_props["world_state_inicial"]["properties"]["objetivo"])
    assert _es_descr_espanol(
        creacion_props["personaje"]["properties"]["inventario_inicial"]["items"]
    )
    assert _es_descr_espanol(creacion_props["primera_escena"]["properties"]["opciones"]["items"])
