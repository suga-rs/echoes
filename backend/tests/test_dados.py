"""Tests del core de tiradas: band→DC, roller d20, clasificación, modificador.

Funciones puras y deterministas (rng inyectable). Ver specs/skill-checks y
specs/character-sheet del cambio add-d20-skill-checks.
"""

import random

import pytest

from app.models.domain import Banda, ResultadoTirada
from app.services.dados import (
    clasificar_tirada,
    dc_de_banda,
    modificador,
    tirar_d20,
    tirar_d20_con_desventaja,
)

# --- 1.1 band → DC -----------------------------------------------------------


@pytest.mark.parametrize(
    ("banda", "dc"),
    [
        (Banda.TRIVIAL, 5),
        (Banda.FACIL, 10),
        (Banda.MEDIA, 15),
        (Banda.DIFICIL, 20),
        (Banda.HEROICA, 25),
    ],
)
def test_banda_mapea_a_su_dc(banda: Banda, dc: int):
    assert dc_de_banda(banda) == dc


# --- 1.2 d20 roller determinista ---------------------------------------------


def test_tirar_d20_en_rango():
    rng = random.Random(0)
    for _ in range(200):
        assert 1 <= tirar_d20(rng) <= 20


def test_tirar_d20_determinista_bajo_semilla():
    a = tirar_d20(random.Random(42))
    b = tirar_d20(random.Random(42))
    assert a == b


# --- desventaja: 2d20 y se queda con el peor ---------------------------------


def test_sin_desventaja_tira_un_solo_d20():
    # Sin desventaja consume una sola tirada: igual secuencia que tirar_d20.
    esperado = tirar_d20(random.Random(7))
    obtenido = tirar_d20_con_desventaja(random.Random(7), desventaja=False)
    assert obtenido == esperado


def test_desventaja_se_queda_con_el_peor():
    # Con la misma semilla, los dos primeros draws son los dos d20; el resultado
    # es el mínimo de ambos.
    rng = random.Random(7)
    d1 = tirar_d20(rng)
    d2 = tirar_d20(rng)
    obtenido = tirar_d20_con_desventaja(random.Random(7), desventaja=True)
    assert obtenido == min(d1, d2)


def test_desventaja_determinista_bajo_semilla():
    a = tirar_d20_con_desventaja(random.Random(99), desventaja=True)
    b = tirar_d20_con_desventaja(random.Random(99), desventaja=True)
    assert a == b


# --- 1.3 clasificación de tiers ----------------------------------------------


def test_total_iguala_o_supera_dc_es_exito():
    # d20=11, mod=+4 → total 15 vs DC 15
    assert clasificar_tirada(d20=11, modificador_total=4, dc=15) == ResultadoTirada.EXITO


def test_total_por_debajo_de_dc_es_fracaso():
    # d20=6, mod=+2 → total 8 vs DC 15
    assert clasificar_tirada(d20=6, modificador_total=2, dc=15) == ResultadoTirada.FRACASO


def test_nat_20_siempre_exito_critico():
    # nat 20 aun con modificador negativo y DC altísimo
    assert clasificar_tirada(d20=20, modificador_total=-5, dc=25) == ResultadoTirada.EXITO_CRITICO


def test_nat_1_siempre_fracaso_critico():
    # nat 1 aun con modificador alto y DC bajísimo
    assert clasificar_tirada(d20=1, modificador_total=10, dc=5) == ResultadoTirada.FRACASO_CRITICO


# --- 1.4 modificador floor((score-10)/2) -------------------------------------


@pytest.mark.parametrize(
    ("score", "mod"),
    [
        (3, -4),
        (7, -2),
        (10, 0),
        (11, 0),
        (16, 3),
        (18, 4),
    ],
)
def test_modificador_de_score(score: int, mod: int):
    assert modificador(score) == mod
