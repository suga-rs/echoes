"""Core de tiradas d20: funciones puras y deterministas.

El dado se tira en el servidor y es la fuente de verdad: la animación del
frontend solo MUESTRA este resultado, nunca lo decide (ver design.md D1/D8).
Todo acá es sin estado ni I/O para poder testearse con un `random.Random`
sembrado.
"""

import math
import random

from app.models.domain import Banda, ResultadoTirada

# El sistema es dueño del número: el narrador elige la banda, no el DC.
BANDA_A_DC: dict[Banda, int] = {
    Banda.TRIVIAL: 5,
    Banda.FACIL: 10,
    Banda.MEDIA: 15,
    Banda.DIFICIL: 20,
    Banda.HEROICA: 25,
}


def dc_de_banda(banda: Banda) -> int:
    """DC fijo de una banda de dificultad."""
    return BANDA_A_DC[banda]


def modificador(score: int) -> int:
    """Modificador estándar de D&D para un puntaje de habilidad."""
    return math.floor((score - 10) / 2)


def tirar_d20(rng: random.Random | None = None) -> int:
    """Tira un d20 real (1-20). `rng` es inyectable para tests deterministas."""
    rng = rng or random.Random()
    return rng.randint(1, 20)


def clasificar_tirada(*, d20: int, modificador_total: int, dc: int) -> ResultadoTirada:
    """Clasifica el resultado. Un 20 natural siempre es éxito crítico y un 1
    natural siempre es fracaso crítico, independientes del modificador y el DC.
    En el resto, total ≥ DC es éxito y total < DC es fracaso."""
    if d20 == 20:
        return ResultadoTirada.EXITO_CRITICO
    if d20 == 1:
        return ResultadoTirada.FRACASO_CRITICO
    if d20 + modificador_total >= dc:
        return ResultadoTirada.EXITO
    return ResultadoTirada.FRACASO
