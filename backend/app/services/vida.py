"""Core de puntos de vida, daño, condiciones y curación: funciones puras.

El sistema es dueño del número (mismo principio que el d20 en `dados.py`): el
narrador declara una BANDA de severidad, nunca PV crudos, y acá se mapea a una
FRACCIÓN de pv_max. Todo es sin estado ni I/O para poder testearse de forma
determinista. Ver design.md (D1/D3/D5/D7) del cambio add-hp-conditions.
"""

import math

from app.models.domain import (
    BandaSeveridad,
    Condicion,
    EfectoCondicion,
)

# --- pv_max derivado de la constitución --------------------------------------
# Pool base más un término por modificador de constitución. Sin niveles, pv_max
# es fijo por partida. Los valores son perillas de tuning (ver design.md).
PV_BASE = 20
PV_POR_MOD_CON = 4
PV_MINIMO = 6


def pv_max_de_constitucion(constitucion: int) -> int:
    """Deriva el pool máximo de PV de la constitución. Mayor constitución, mayor
    pool. Nunca por debajo de PV_MINIMO."""
    mod = math.floor((constitucion - 10) / 2)
    return max(PV_MINIMO, PV_BASE + PV_POR_MOD_CON * mod)


# --- daño por fracción de pv_max ---------------------------------------------
# El narrador elige la banda; el sistema posee la fracción. Monótona creciente.
SEVERIDAD_A_FRACCION: dict[BandaSeveridad, float] = {
    BandaSeveridad.RASGUNO: 0.05,
    BandaSeveridad.LEVE: 0.15,
    BandaSeveridad.GRAVE: 0.30,
    BandaSeveridad.SEVERO: 0.50,
    BandaSeveridad.MORTAL: 1.0,
}

# Tick de daño por turno (envenenado, sangrando) como fracción de pv_max.
FRACCION_DANO_POR_TURNO = 0.10

# Curación del sistema (el narrador declara la intención, no el número).
FRACCION_CURACION_DESCANSO = 0.50
FRACCION_CURACION_POCION = 0.40


def calcular_dano(pv_max: int, banda: BandaSeveridad) -> int:
    """PV a descontar para una banda de severidad: ceil(fracción * pv_max), al
    menos 1. `mortal` devuelve pv_max, alcanzando para llevar a 0 cualquier
    pv_actual."""
    return max(1, math.ceil(SEVERIDAD_A_FRACCION[banda] * pv_max))


def dano_por_turno(pv_max: int) -> int:
    """Daño de un tick de condición por turno: al menos 1 PV."""
    return max(1, math.ceil(FRACCION_DANO_POR_TURNO * pv_max))


def curacion_descanso(pv_max: int) -> int:
    """PV recuperados por un descanso declarado por el narrador."""
    return max(1, math.ceil(FRACCION_CURACION_DESCANSO * pv_max))


def curacion_pocion(pv_max: int) -> int:
    """PV recuperados por consumir una poción del inventario."""
    return max(1, math.ceil(FRACCION_CURACION_POCION * pv_max))


def aplicar_dano(pv_actual: int, dano: int) -> int:
    """Resta daño sin bajar de 0."""
    return max(0, pv_actual - dano)


def aplicar_curacion(*, pv_actual: int, pv_max: int, cantidad: int) -> int:
    """Suma curación sin pasar pv_max."""
    return min(pv_max, pv_actual + cantidad)


# --- condiciones -------------------------------------------------------------


def tiene_desventaja(condiciones: list[Condicion]) -> bool:
    """True si alguna condición activa impone desventaja en las tiradas."""
    return any(c.efecto == EfectoCondicion.DESVENTAJA for c in condiciones)


def tick_condiciones(
    condiciones: list[Condicion], *, pv_max: int, pv_actual: int
) -> tuple[list[Condicion], int, int]:
    """Aplica un turno de las condiciones activas: descuenta el daño por turno,
    decrementa las duraciones numéricas y descarta las que expiran. Las
    duraciones no numéricas (hasta_curar / hasta_evento) persisten. Devuelve
    (condiciones_sobrevivientes, nuevo_pv_actual, dano_total)."""
    dano_total = 0
    sobrevivientes: list[Condicion] = []
    for c in condiciones:
        if c.efecto == EfectoCondicion.DANO_POR_TURNO:
            dano_total += dano_por_turno(pv_max)
        if isinstance(c.duracion, int):
            restante = c.duracion - 1
            if restante >= 1:
                sobrevivientes.append(Condicion(tipo=c.tipo, efecto=c.efecto, duracion=restante))
            # restante < 1 → la condición expiró este turno: no se conserva.
        else:
            sobrevivientes.append(c)
    return sobrevivientes, aplicar_dano(pv_actual, dano_total), dano_total
