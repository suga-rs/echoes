"""Tests de seeds creativas y armado del prompt de creación."""

import random

import pytest

from app.models.domain import Genero
from app.services.prompts import (
    CREATION_POOLS,
    SemillaCreativa,
    build_creacion_user_prompt,
    sample_seed,
)

TODOS_LOS_GENEROS = list(Genero)


# --- sample_seed -------------------------------------------------------------


@pytest.mark.parametrize("genero", TODOS_LOS_GENEROS)
def test_sample_seed_es_determinista_con_rng_sembrado(genero):
    a = sample_seed(genero, random.Random(42))
    b = sample_seed(genero, random.Random(42))
    assert a == b


@pytest.mark.parametrize("genero", TODOS_LOS_GENEROS)
def test_sample_seed_devuelve_valores_de_los_pools(genero):
    seed = sample_seed(genero, random.Random(7))
    pools = CREATION_POOLS[genero]
    assert seed.nombre in pools["nombres"]
    assert seed.premisa in pools["premisas"]
    assert seed.tono in pools["tonos"]
    assert seed.apertura in pools["aperturas"]


@pytest.mark.parametrize("genero", TODOS_LOS_GENEROS)
def test_sample_seed_completa_todas_las_dimensiones(genero):
    seed = sample_seed(genero)
    assert isinstance(seed, SemillaCreativa)
    assert seed.nombre and seed.premisa and seed.tono and seed.apertura


# --- build_creacion_user_prompt ---------------------------------------------


def _seed_fija() -> SemillaCreativa:
    return SemillaCreativa(
        nombre="SEED_NOMBRE",
        premisa="SEED_PREMISA",
        tono="SEED_TONO",
        apertura="SEED_APERTURA",
    )


def test_prompt_usa_seed_como_inspiracion_sin_input_jugador():
    prompt = build_creacion_user_prompt(Genero.FANTASIA, "una herrera huérfana", _seed_fija())
    assert "SEMILLA CREATIVA" in prompt
    assert "SEED_PREMISA" in prompt
    assert "SEED_TONO" in prompt
    assert "SEED_APERTURA" in prompt


def test_prompt_honra_premisa_del_jugador_y_descarta_la_de_la_seed():
    prompt = build_creacion_user_prompt(
        Genero.FANTASIA,
        "una herrera huérfana",
        _seed_fija(),
        premisa="vengar a su maestro asesinado",
    )
    assert "vengar a su maestro asesinado" in prompt
    # La premisa del jugador se honra; la de la seed no debe aparecer.
    assert "SEED_PREMISA" not in prompt
    # Pero el tono de la seed sí (el jugador no lo dio).
    assert "SEED_TONO" in prompt


def test_prompt_honra_tono_del_jugador_y_descarta_el_de_la_seed():
    prompt = build_creacion_user_prompt(
        Genero.TERROR,
        "un faro",
        _seed_fija(),
        tono="opresivo y húmedo",
    )
    assert "opresivo y húmedo" in prompt
    assert "SEED_TONO" not in prompt
    assert "SEED_PREMISA" in prompt


def test_prompt_marca_seccion_de_input_del_jugador_cuando_lo_hay():
    prompt = build_creacion_user_prompt(
        Genero.FANTASIA,
        "una herrera",
        _seed_fija(),
        premisa="encontrar a su hermana",
    )
    assert "JUGADOR" in prompt


def test_prompt_incluye_precedencia_de_nombre():
    prompt = build_creacion_user_prompt(Genero.FANTASIA, "una herrera", _seed_fija())
    # El nombre de la seed es solo respaldo; el del jugador (si lo da) manda.
    assert "respaldo" in prompt.lower()
    assert "SEED_NOMBRE" in prompt
