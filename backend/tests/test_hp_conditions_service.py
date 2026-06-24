"""Tests de PV/condiciones en el servicio: daño, curación, condiciones, muerte
y paridad entre el path síncrono y el de streaming. Ver specs/hp-conditions.
"""

import asyncio
import json
import random

from factories import fake_turno_llm_response

from app.models.domain import (
    Condicion,
    DuracionCondicion,
    EfectoCondicion,
    EstadoPartida,
    TipoCondicion,
    TipoFinal,
)
from app.services import dados, vida
from app.services.partida_service import PartidaService


def _turno_con_consecuencia(**consecuencia) -> dict:
    base = fake_turno_llm_response()
    base["consecuencia"] = {
        "dano": None,
        "condicion_aplicar": None,
        "condicion_quitar": None,
        "descanso": False,
        "curar_pocion": None,
        **consecuencia,
    }
    return base


def _svc(foundry_mock, partida_repo_mock, imagen_repo_mock, **kw) -> PartidaService:
    return PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock, **kw
    )


def _guardada(partida_repo_mock):
    return partida_repo_mock.upsert.call_args[0][0]


# --- daño por banda ----------------------------------------------------------


def test_dano_por_banda_descuenta_pv(
    foundry_mock, partida_repo_mock, imagen_repo_mock, partida_de_ejemplo
):
    partida_repo_mock.get.return_value = partida_de_ejemplo
    pv0 = partida_de_ejemplo.personaje.pv_actual
    foundry_mock.chat_json_raw.return_value = ("{}", _turno_con_consecuencia(dano="grave"))

    svc = _svc(foundry_mock, partida_repo_mock, imagen_repo_mock)
    resp = svc.avanzar_turno("test-abc-123", "cruzar el puente podrido")

    esperado = vida.calcular_dano(partida_de_ejemplo.personaje.pv_max, _banda("grave"))
    assert _guardada(partida_repo_mock).personaje.pv_actual == pv0 - esperado
    assert resp.dano_recibido == esperado
    assert resp.pv_actual == pv0 - esperado


def test_dano_sin_tirada_previa(
    foundry_mock, partida_repo_mock, imagen_repo_mock, partida_de_ejemplo
):
    # consecuencia es independiente de requiere_tirada: una trampa daña sin check.
    partida_repo_mock.get.return_value = partida_de_ejemplo
    payload = _turno_con_consecuencia(dano="leve")
    assert payload["requiere_tirada"] is None
    foundry_mock.chat_json_raw.return_value = ("{}", payload)

    svc = _svc(foundry_mock, partida_repo_mock, imagen_repo_mock)
    svc.avanzar_turno("test-abc-123", "pisar la baldosa floja")

    assert foundry_mock.chat_json_raw.call_count == 1  # una sola llamada, sin tirada
    assert _guardada(partida_repo_mock).personaje.pv_actual < partida_de_ejemplo.personaje.pv_max


# --- muerte por 0 PV ---------------------------------------------------------


def test_dano_mortal_termina_en_fracaso(
    foundry_mock, partida_repo_mock, imagen_repo_mock, partida_de_ejemplo
):
    partida_repo_mock.get.return_value = partida_de_ejemplo
    foundry_mock.chat_json_raw.return_value = ("{}", _turno_con_consecuencia(dano="mortal"))
    foundry_mock.generar_imagen.return_value = b"\x89PNG" + b"\x00" * 100
    imagen_repo_mock.subir_imagen.return_value = "https://fake.blob/x.png"

    svc = _svc(foundry_mock, partida_repo_mock, imagen_repo_mock)
    resp = svc.avanzar_turno("test-abc-123", "encarar al dragón sin escudo")

    g = _guardada(partida_repo_mock)
    assert g.personaje.pv_actual == 0
    assert g.metadata.estado == EstadoPartida.FINALIZADA
    assert g.metadata.final == TipoFinal.FRACASO
    assert g.metadata.razon_fin
    assert resp.estado == EstadoPartida.FINALIZADA


# --- condiciones -------------------------------------------------------------


def test_aplicar_condicion(foundry_mock, partida_repo_mock, imagen_repo_mock, partida_de_ejemplo):
    partida_repo_mock.get.return_value = partida_de_ejemplo
    cons = _turno_con_consecuencia(
        condicion_aplicar={"tipo": "envenenado", "efecto": "dano_por_turno", "duracion": 3}
    )
    foundry_mock.chat_json_raw.return_value = ("{}", cons)

    svc = _svc(foundry_mock, partida_repo_mock, imagen_repo_mock)
    svc.avanzar_turno("test-abc-123", "tomar el agua turbia")

    condiciones = _guardada(partida_repo_mock).personaje.condiciones
    assert any(c.tipo == TipoCondicion.ENVENENADO for c in condiciones)


def test_quitar_condicion(foundry_mock, partida_repo_mock, imagen_repo_mock, partida_de_ejemplo):
    partida_de_ejemplo.personaje.condiciones = [
        Condicion(
            tipo=TipoCondicion.ENVENENADO,
            efecto=EfectoCondicion.DANO_POR_TURNO,
            duracion=DuracionCondicion.HASTA_CURAR,
        )
    ]
    partida_repo_mock.get.return_value = partida_de_ejemplo
    foundry_mock.chat_json_raw.return_value = (
        "{}",
        _turno_con_consecuencia(condicion_quitar="envenenado"),
    )

    svc = _svc(foundry_mock, partida_repo_mock, imagen_repo_mock)
    svc.avanzar_turno("test-abc-123", "beber el antídoto")

    assert _guardada(partida_repo_mock).personaje.condiciones == []


def test_dano_por_turno_tickea_al_inicio(
    foundry_mock, partida_repo_mock, imagen_repo_mock, partida_de_ejemplo
):
    partida_de_ejemplo.personaje.condiciones = [
        Condicion(
            tipo=TipoCondicion.SANGRANDO,
            efecto=EfectoCondicion.DANO_POR_TURNO,
            duracion=DuracionCondicion.HASTA_CURAR,
        )
    ]
    pv0 = partida_de_ejemplo.personaje.pv_actual
    partida_repo_mock.get.return_value = partida_de_ejemplo
    foundry_mock.chat_json_raw.return_value = ("{}", _turno_con_consecuencia())

    svc = _svc(foundry_mock, partida_repo_mock, imagen_repo_mock)
    resp = svc.avanzar_turno("test-abc-123", "seguir caminando")

    tick = vida.dano_por_turno(partida_de_ejemplo.personaje.pv_max)
    assert _guardada(partida_repo_mock).personaje.pv_actual == pv0 - tick
    assert resp.dano_recibido == tick


# --- curación ----------------------------------------------------------------


def test_pocion_cura_y_se_consume(
    foundry_mock, partida_repo_mock, imagen_repo_mock, partida_de_ejemplo
):
    partida_de_ejemplo.personaje.inventario.append("poción de vida")
    partida_de_ejemplo.personaje.pv_actual = 3
    partida_repo_mock.get.return_value = partida_de_ejemplo
    foundry_mock.chat_json_raw.return_value = (
        "{}",
        _turno_con_consecuencia(curar_pocion="poción de vida"),
    )

    svc = _svc(foundry_mock, partida_repo_mock, imagen_repo_mock)
    svc.avanzar_turno("test-abc-123", "beber la poción")

    g = _guardada(partida_repo_mock)
    assert g.personaje.pv_actual > 3
    assert g.personaje.pv_actual <= g.personaje.pv_max
    assert "poción de vida" not in g.personaje.inventario


def test_descanso_no_supera_pv_max(
    foundry_mock, partida_repo_mock, imagen_repo_mock, partida_de_ejemplo
):
    partida_de_ejemplo.personaje.pv_actual = partida_de_ejemplo.personaje.pv_max - 1
    partida_repo_mock.get.return_value = partida_de_ejemplo
    foundry_mock.chat_json_raw.return_value = ("{}", _turno_con_consecuencia(descanso=True))

    svc = _svc(foundry_mock, partida_repo_mock, imagen_repo_mock)
    svc.avanzar_turno("test-abc-123", "acampar junto al fuego")

    g = _guardada(partida_repo_mock)
    assert g.personaje.pv_actual == g.personaje.pv_max


# --- desventaja por condición ------------------------------------------------


def test_condicion_desventaja_tira_2d20_y_se_queda_con_el_peor(
    foundry_mock, partida_repo_mock, imagen_repo_mock, partida_de_ejemplo
):
    partida_de_ejemplo.personaje.condiciones = [
        Condicion(
            tipo=TipoCondicion.ATURDIDO,
            efecto=EfectoCondicion.DESVENTAJA,
            duracion=DuracionCondicion.HASTA_CURAR,
        )
    ]
    partida_repo_mock.get.return_value = partida_de_ejemplo
    fase1 = {
        **fake_turno_llm_response(),
        "requiere_tirada": {"habilidad": "destreza", "banda": "media"},
    }
    foundry_mock.chat_json_raw.side_effect = [
        ("{}", fase1),
        ("{}", _turno_con_consecuencia()),
    ]

    svc = _svc(foundry_mock, partida_repo_mock, imagen_repo_mock, rng=random.Random(123))
    svc.avanzar_turno("test-abc-123", "esquivar la trampa")

    # Con la misma semilla, el d20 esperado es el menor de las dos primeras tiradas.
    rng = random.Random(123)
    d1, d2 = dados.tirar_d20(rng), dados.tirar_d20(rng)
    assert _guardada(partida_repo_mock).historial[-1].tirada.d20 == min(d1, d2)


# --- paridad sync / stream ---------------------------------------------------


def _run_stream(svc, accion: str) -> None:
    async def _run():
        return [e async for e in svc.avanzar_turno_stream("test-abc-123", accion)]

    asyncio.run(_run())


def test_paridad_dano_sync_y_stream(
    foundry_mock, partida_repo_mock, imagen_repo_mock, partida_de_ejemplo
):
    # Mismo daño declarado debe dejar el mismo pv_actual por ambos caminos.
    partida_repo_mock.get.return_value = partida_de_ejemplo
    pv0 = partida_de_ejemplo.personaje.pv_actual
    payload = _turno_con_consecuencia(dano="grave")

    # Sync
    foundry_mock.chat_json_raw.return_value = ("{}", payload)
    svc = _svc(foundry_mock, partida_repo_mock, imagen_repo_mock)
    svc.avanzar_turno("test-abc-123", "trepar el muro")
    pv_sync = _guardada(partida_repo_mock).personaje.pv_actual

    # Stream: reseteamos pv_actual a pv0 (el upsert mutó la instancia compartida)
    partida_de_ejemplo.personaje.pv_actual = pv0
    partida_de_ejemplo.personaje.condiciones = []

    def _make_gen(p: str):
        async def gen(_s, _u):
            yield p

        return gen

    foundry_mock.chat_streaming_async.side_effect = lambda s, u: _make_gen(json.dumps(payload))(
        s, u
    )
    svc2 = _svc(foundry_mock, partida_repo_mock, imagen_repo_mock)
    _run_stream(svc2, "trepar el muro")
    pv_stream = _guardada(partida_repo_mock).personaje.pv_actual

    assert (
        pv_sync
        == pv_stream
        == pv0 - vida.calcular_dano(partida_de_ejemplo.personaje.pv_max, _banda("grave"))
    )


def _banda(value: str):
    from app.models.domain import BandaSeveridad

    return BandaSeveridad(value)
