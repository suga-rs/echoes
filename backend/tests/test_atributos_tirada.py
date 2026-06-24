"""Modelos de ficha (Atributos) y de tirada (Tirada), con retrocompatibilidad.

Cosmos es schemaless: las partidas previas a este cambio deben deserializar
con defaults seguros (ver specs/character-sheet y specs/skill-checks).
"""

import pytest
from pydantic import ValidationError

from app.models.domain import Atributos, Banda, Habilidad, Personaje, ResultadoTirada, Tirada

# --- Atributos ---------------------------------------------------------------


def test_atributos_modificadores_estandar():
    attrs = Atributos(
        fuerza=16, destreza=7, constitucion=10, inteligencia=18, sabiduria=11, carisma=3
    )
    assert attrs.modificador(Habilidad.FUERZA) == 3
    assert attrs.modificador(Habilidad.DESTREZA) == -2
    assert attrs.modificador(Habilidad.CONSTITUCION) == 0
    assert attrs.modificador(Habilidad.INTELIGENCIA) == 4
    assert attrs.modificador(Habilidad.CARISMA) == -4


def test_atributos_rechaza_fuera_de_rango():
    with pytest.raises(ValidationError):
        Atributos(
            fuerza=19, destreza=10, constitucion=10, inteligencia=10, sabiduria=10, carisma=10
        )
    with pytest.raises(ValidationError):
        Atributos(fuerza=2, destreza=10, constitucion=10, inteligencia=10, sabiduria=10, carisma=10)


# --- Retrocompatibilidad: Personaje legacy sin atributos ---------------------


def test_personaje_legacy_sin_atributos_default_neutral():
    # Documento previo al cambio: sin atributos, deserializa con los seis en 10 (+0).
    pj = Personaje.model_validate(
        {
            "nombre": "Lyra",
            "descripcion_narrativa": "Arqueóloga escéptica.",
            "descripcion_visual_en": "Woman around 40, dark hair.",
        }
    )
    assert pj.atributos.fuerza == 10
    assert pj.atributos.destreza == 10
    assert pj.atributos.constitucion == 10
    assert pj.atributos.inteligencia == 10
    assert pj.atributos.sabiduria == 10
    assert pj.atributos.carisma == 10
    assert pj.atributos.modificador(Habilidad.FUERZA) == 0


# --- Tirada persistida en el turno -------------------------------------------


def test_tirada_persiste_los_campos():
    t = Tirada(
        habilidad=Habilidad.DESTREZA,
        banda=Banda.MEDIA,
        dc=15,
        d20=11,
        modificador=4,
        total=15,
        resultado=ResultadoTirada.EXITO,
    )
    assert t.habilidad == Habilidad.DESTREZA
    assert t.dc == 15
    assert t.total == 15
    assert t.resultado == ResultadoTirada.EXITO


def test_turno_legacy_sin_tirada_default_none():
    from app.models.domain import TurnoHistorial

    turno = TurnoHistorial.model_validate(
        {
            "turno": 2,
            "accion_jugador": "Avanzar",
            "narrativa": "N",
            "opciones": ["a", "b", "c"],
        }
    )
    assert turno.tirada is None
