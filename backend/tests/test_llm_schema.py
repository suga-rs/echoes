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


_NPC_VALIDO = {
    "nombre": "Eldrin",
    "descripcion": "Un ermitaño",
    "actitud": "neutral",
    "descripcion_visual_en": "Old hermit, long white beard, tattered grey robe, wooden staff",
}

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


# ----------------------------------------------------- TURNO: consistencia visual de NPCs


def test_turno_npc_encontrado_con_visual_es_valido():
    payload = _con(
        fake_turno_llm_response(),
        ["actualizaciones_estado", "npc_encontrado"],
        _NPC_VALIDO,
    )
    validate(payload, TURNO_JSON_SCHEMA)
    modelo = TurnoLLMResponse.model_validate(payload)
    assert modelo.actualizaciones_estado.npc_encontrado.descripcion_visual_en.startswith("Old")


def test_turno_npc_encontrado_sin_visual_falla():
    """descripcion_visual_en es requerido cuando se introduce un NPC."""
    payload = _con(
        fake_turno_llm_response(),
        ["actualizaciones_estado", "npc_encontrado"],
        _sin(_NPC_VALIDO, ["descripcion_visual_en"]),
    )
    with pytest.raises(ValidationError):
        validate(payload, TURNO_JSON_SCHEMA)


def test_turno_npcs_en_escena_valido():
    payload = _con(
        fake_turno_llm_response(),
        ["generar_imagen", "npcs_en_escena"],
        ["Eldrin", "Gorad"],
    )
    validate(payload, TURNO_JSON_SCHEMA)
    modelo = TurnoLLMResponse.model_validate(payload)
    assert modelo.generar_imagen.npcs_en_escena == ["Eldrin", "Gorad"]


def test_turno_npcs_en_escena_ausente_default_lista_vacia():
    """npcs_en_escena es opcional: ausente deserializa como lista vacía."""
    payload = fake_turno_llm_response()
    assert "npcs_en_escena" not in payload["generar_imagen"]
    validate(payload, TURNO_JSON_SCHEMA)
    modelo = TurnoLLMResponse.model_validate(payload)
    assert modelo.generar_imagen.npcs_en_escena == []


def test_turno_npcs_en_escena_tipo_invalido_falla():
    payload = _con(fake_turno_llm_response(), ["generar_imagen", "npcs_en_escena"], "Eldrin")
    with pytest.raises(ValidationError):
        validate(payload, TURNO_JSON_SCHEMA)


# ----------------------------------------------------- TURNO: requiere_tirada (fase 1)


def test_turno_requiere_tirada_null_es_valido():
    # Una acción trivial/imposible declara requiere_tirada = null (presente, no ausente).
    payload = fake_turno_llm_response()
    assert payload["requiere_tirada"] is None
    validate(payload, TURNO_JSON_SCHEMA)
    modelo = TurnoLLMResponse.model_validate(payload)
    assert modelo.requiere_tirada is None


def test_turno_omitir_requiere_tirada_falla():
    # El campo es REQUERIDO (aunque nullable): omitirlo del todo es inválido.
    # Forzar su presencia es la palanca para que el modelo deje de ignorarlo.
    with pytest.raises(ValidationError):
        validate(_sin(fake_turno_llm_response(), ["requiere_tirada"]), TURNO_JSON_SCHEMA)


def test_turno_con_requiere_tirada_valido():
    payload = _con(
        fake_turno_llm_response(),
        ["requiere_tirada"],
        {"habilidad": "destreza", "banda": "media"},
    )
    validate(payload, TURNO_JSON_SCHEMA)
    modelo = TurnoLLMResponse.model_validate(payload)
    assert modelo.requiere_tirada is not None
    assert modelo.requiere_tirada.habilidad == "destreza"
    assert modelo.requiere_tirada.banda == "media"


def test_turno_requiere_tirada_nula_valida():
    payload = _con(fake_turno_llm_response(), ["requiere_tirada"], None)
    validate(payload, TURNO_JSON_SCHEMA)
    assert TurnoLLMResponse.model_validate(payload).requiere_tirada is None


@pytest.mark.parametrize(
    "tirada",
    [
        pytest.param({"habilidad": "magia", "banda": "media"}, id="habilidad-invalida"),
        pytest.param({"habilidad": "destreza", "banda": "imposible"}, id="banda-invalida"),
        pytest.param({"habilidad": "destreza"}, id="falta-banda"),
        pytest.param({"banda": "media"}, id="falta-habilidad"),
        pytest.param({"habilidad": "destreza", "banda": "media", "dc": 15}, id="dc-no-permitido"),
    ],
)
def test_turno_requiere_tirada_invalida_falla(tirada: dict):
    payload = _con(fake_turno_llm_response(), ["requiere_tirada"], tirada)
    with pytest.raises(ValidationError):
        validate(payload, TURNO_JSON_SCHEMA)


# ----------------------------------------------------- TURNO: consecuencia (HP/condiciones)

_CONSECUENCIA_VALIDA = {
    "dano": "grave",
    "condicion_aplicar": {
        "tipo": "envenenado",
        "efecto": "dano_por_turno",
        "duracion": 3,
    },
    "condicion_quitar": None,
    "descanso": False,
    "curar_pocion": None,
}


def test_turno_consecuencia_null_es_valido():
    payload = fake_turno_llm_response()
    assert payload["consecuencia"] is None
    validate(payload, TURNO_JSON_SCHEMA)
    assert TurnoLLMResponse.model_validate(payload).consecuencia is None


def test_turno_omitir_consecuencia_falla():
    # Requerido aunque nullable: igual que requiere_tirada, su presencia es la
    # palanca para que el modelo lo decida conscientemente.
    with pytest.raises(ValidationError):
        validate(_sin(fake_turno_llm_response(), ["consecuencia"]), TURNO_JSON_SCHEMA)


def test_turno_con_consecuencia_valida():
    payload = _con(fake_turno_llm_response(), ["consecuencia"], _CONSECUENCIA_VALIDA)
    validate(payload, TURNO_JSON_SCHEMA)
    modelo = TurnoLLMResponse.model_validate(payload)
    assert modelo.consecuencia is not None
    assert modelo.consecuencia.dano == "grave"
    assert modelo.consecuencia.condicion_aplicar.efecto == "dano_por_turno"


def test_turno_consecuencia_duracion_sentinel_valida():
    cons = {**_CONSECUENCIA_VALIDA}
    cons["condicion_aplicar"] = {
        "tipo": "aturdido",
        "efecto": "desventaja",
        "duracion": "hasta_curar",
    }
    payload = _con(fake_turno_llm_response(), ["consecuencia"], cons)
    validate(payload, TURNO_JSON_SCHEMA)


@pytest.mark.parametrize(
    "consecuencia",
    [
        pytest.param({**_CONSECUENCIA_VALIDA, "dano": "letal"}, id="banda-severidad-invalida"),
        pytest.param(_sin(_CONSECUENCIA_VALIDA, ["descanso"]), id="falta-descanso"),
        pytest.param({**_CONSECUENCIA_VALIDA, "foo": "bar"}, id="clave-extra"),
        pytest.param(
            {
                **_CONSECUENCIA_VALIDA,
                "condicion_aplicar": {
                    "tipo": "envenenado",
                    "efecto": "fuego",
                    "duracion": 3,
                },
            },
            id="efecto-invalido",
        ),
        pytest.param(
            {
                **_CONSECUENCIA_VALIDA,
                "condicion_aplicar": {
                    "tipo": "envenenado",
                    "efecto": "dano_por_turno",
                    "duracion": "para_siempre",
                },
            },
            id="duracion-sentinel-invalido",
        ),
        pytest.param({**_CONSECUENCIA_VALIDA, "condicion_quitar": "maldito"}, id="quitar-invalido"),
    ],
)
def test_turno_consecuencia_invalida_falla(consecuencia: dict):
    payload = _con(fake_turno_llm_response(), ["consecuencia"], consecuencia)
    with pytest.raises(ValidationError):
        validate(payload, TURNO_JSON_SCHEMA)


# --------------------------------------------------------------------------- CREACION


def test_creacion_baseline_valido():
    payload = fake_creacion_llm_response()
    validate(payload, CREACION_JSON_SCHEMA)  # no debe lanzar
    modelo = CreacionLLMResponse.model_validate(payload)
    assert modelo.personaje.nombre == "Lyra"
    assert len(modelo.primera_escena.opciones) == 3


def test_creacion_incluye_los_seis_atributos():
    payload = fake_creacion_llm_response()
    modelo = CreacionLLMResponse.model_validate(payload)
    attrs = modelo.personaje.atributos
    assert attrs.fuerza == 11
    assert attrs.destreza == 13
    assert attrs.constitucion == 12
    assert attrs.inteligencia == 16
    assert attrs.sabiduria == 14
    assert attrs.carisma == 10


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
    pytest.param(
        _sin(fake_creacion_llm_response(), ["personaje", "atributos"]), id="falta-atributos"
    ),
    pytest.param(
        _sin(fake_creacion_llm_response(), ["personaje", "atributos", "fuerza"]),
        id="falta-una-habilidad",
    ),
    pytest.param(
        _con(fake_creacion_llm_response(), ["personaje", "atributos", "fuerza"], 19),
        id="atributo-sobre-18",
    ),
    pytest.param(
        _con(fake_creacion_llm_response(), ["personaje", "atributos", "fuerza"], 2),
        id="atributo-bajo-3",
    ),
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
