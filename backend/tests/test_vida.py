"""Core de PV, daño por fracción, curación y ticks de condición: funciones puras.

El sistema es dueño del número (igual que el d20): el narrador declara una banda
de severidad, nunca PV crudos. Ver specs/hp-conditions del cambio add-hp-conditions.
"""

import pytest

from app.models.domain import (
    BandaSeveridad,
    Condicion,
    DuracionCondicion,
    EfectoCondicion,
    TipoCondicion,
)
from app.services import vida

# --- pv_max derivado de la constitución --------------------------------------


@pytest.mark.parametrize("con", [3, 7, 10, 14, 18])
def test_pv_max_nunca_bajo_el_minimo(con: int):
    assert vida.pv_max_de_constitucion(con) >= vida.PV_MINIMO


def test_pv_max_mayor_con_mas_constitucion():
    assert vida.pv_max_de_constitucion(18) > vida.pv_max_de_constitucion(10)
    assert vida.pv_max_de_constitucion(10) > vida.pv_max_de_constitucion(6)


# --- daño por fracción de pv_max ---------------------------------------------


def test_dano_es_al_menos_uno_para_cualquier_banda():
    for banda in BandaSeveridad:
        assert vida.calcular_dano(40, banda) >= 1


def test_dano_mayor_banda_remueve_mas():
    pv = 40
    assert vida.calcular_dano(pv, BandaSeveridad.SEVERO) > vida.calcular_dano(
        pv, BandaSeveridad.LEVE
    )


def test_mortal_zera_al_personaje():
    # mortal debe alcanzar para llevar pv_actual a 0 desde pv_max
    pv_max = 33
    dano = vida.calcular_dano(pv_max, BandaSeveridad.MORTAL)
    assert pv_max - dano <= 0


def test_aplicar_dano_no_baja_de_cero():
    assert vida.aplicar_dano(5, 12) == 0


# --- curación capada en pv_max -----------------------------------------------


def test_curacion_no_supera_pv_max():
    assert vida.aplicar_curacion(pv_actual=30, pv_max=40, cantidad=100) == 40


def test_descanso_y_pocion_curan_algo():
    assert vida.curacion_descanso(40) >= 1
    assert vida.curacion_pocion(40) >= 1


# --- ticks de condición y duración -------------------------------------------


def test_dano_por_turno_descuenta_pv():
    cond = Condicion(
        tipo=TipoCondicion.ENVENENADO, efecto=EfectoCondicion.DANO_POR_TURNO, duracion=3
    )
    sobrevivientes, nuevo_pv, dano = vida.tick_condiciones([cond], pv_max=40, pv_actual=40)
    assert dano == vida.dano_por_turno(40)
    assert nuevo_pv == 40 - dano
    # duración 3 → quedan 2 turnos
    assert sobrevivientes[0].duracion == 2


def test_condicion_con_duracion_expira():
    cond = Condicion(
        tipo=TipoCondicion.SANGRANDO, efecto=EfectoCondicion.DANO_POR_TURNO, duracion=1
    )
    sobrevivientes, _, _ = vida.tick_condiciones([cond], pv_max=40, pv_actual=40)
    assert sobrevivientes == []


def test_duracion_no_numerica_persiste():
    cond = Condicion(
        tipo=TipoCondicion.ATURDIDO,
        efecto=EfectoCondicion.DESVENTAJA,
        duracion=DuracionCondicion.HASTA_CURAR,
    )
    sobrevivientes, _, dano = vida.tick_condiciones([cond], pv_max=40, pv_actual=40)
    assert len(sobrevivientes) == 1
    assert dano == 0  # desventaja no tickea daño


def test_tiene_desventaja_detecta_efecto():
    sin = [
        Condicion(tipo=TipoCondicion.SANGRANDO, efecto=EfectoCondicion.DANO_POR_TURNO, duracion=2)
    ]
    con = [
        Condicion(
            tipo=TipoCondicion.ATURDIDO,
            efecto=EfectoCondicion.DESVENTAJA,
            duracion=DuracionCondicion.HASTA_CURAR,
        )
    ]
    assert vida.tiene_desventaja(sin) is False
    assert vida.tiene_desventaja(con) is True
