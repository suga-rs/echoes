"""Tests del PartidaService con todas las dependencias mockeadas."""

import asyncio
import json
import random

import pytest
from factories import fake_creacion_llm_response, fake_turno_llm_response, metric_points

from app.core.exceptions import (
    FoundryError,
    LimiteImagenesExcedidoError,
    PartidaFinalizadaError,
    PartidaNoEncontradaError,
    RespuestaLLMInvalidaError,
)
from app.models.domain import (
    NPC,
    Actitud,
    EstadoPartida,
    FaseNarrativa,
    Genero,
    Habilidad,
    TipoFinal,
    TurnoHistorial,
)
from app.services import dados
from app.services.partida_service import PartidaService, resolver_npcs_visuales
from app.services.prompts import PROMPT_VERSION, build_turno_user_prompt


def _fase1_con_tirada(habilidad: str = "destreza", banda: str = "media") -> dict:
    return {
        **fake_turno_llm_response(),
        "requiere_tirada": {"habilidad": habilidad, "banda": banda},
    }


def _es_prompt_de_referencia(prompt: str) -> bool:
    return "reference portrait" in prompt.lower()


def test_crear_partida_ok(foundry_mock, partida_repo_mock, imagen_repo_mock):
    foundry_mock.chat_json_raw.return_value = ("{}", fake_creacion_llm_response())
    foundry_mock.generar_imagen.return_value = b"\x89PNG" + b"\x00" * 100
    imagen_repo_mock.subir_imagen.return_value = "https://fake.blob/x.png"

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    resp = svc.crear_partida(Genero.FANTASIA, "una arqueóloga escéptica")

    assert resp.personaje.nombre == "Lyra"
    assert resp.primer_turno.turno == 1
    assert resp.primer_turno.imagen_url == "https://fake.blob/x.png"
    assert len(resp.primer_turno.opciones) == 3
    partida_repo_mock.upsert.assert_called_once()


def test_crear_partida_mapea_atributos_al_personaje(
    foundry_mock, partida_repo_mock, imagen_repo_mock
):
    foundry_mock.chat_json_raw.return_value = ("{}", fake_creacion_llm_response())
    foundry_mock.generar_imagen.return_value = b"\x89PNG" + b"\x00" * 100
    imagen_repo_mock.subir_imagen.return_value = "https://fake.blob/x.png"

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    svc.crear_partida(Genero.FANTASIA, "una arqueóloga escéptica")

    guardada = partida_repo_mock.upsert.call_args[0][0]
    attrs = guardada.personaje.atributos
    assert attrs.inteligencia == 16
    assert attrs.fuerza == 11


def test_crear_partida_persiste_prompt_version(foundry_mock, partida_repo_mock, imagen_repo_mock):
    foundry_mock.chat_json_raw.return_value = ("{}", fake_creacion_llm_response())
    foundry_mock.generar_imagen.return_value = b"\x89PNG" + b"\x00" * 100
    imagen_repo_mock.subir_imagen.return_value = "https://fake.blob/x.png"

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    svc.crear_partida(Genero.FANTASIA, "una arqueóloga escéptica")

    guardada = partida_repo_mock.upsert.call_args[0][0]
    assert guardada.metadata.prompt_version == PROMPT_VERSION


def test_crear_partida_muestrea_seed_e_inyecta_inspiracion(
    foundry_mock, partida_repo_mock, imagen_repo_mock
):
    foundry_mock.chat_json_raw.return_value = ("{}", fake_creacion_llm_response())
    foundry_mock.generar_imagen.return_value = b"\x89PNG" + b"\x00" * 100
    imagen_repo_mock.subir_imagen.return_value = "https://fake.blob/x.png"

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    svc.crear_partida(Genero.FANTASIA, "una arqueóloga escéptica")

    user_prompt = foundry_mock.chat_json_raw.call_args_list[0][0][1]
    assert "SEMILLA CREATIVA" in user_prompt


def test_crear_partida_thread_premisa_y_tono_del_jugador(
    foundry_mock, partida_repo_mock, imagen_repo_mock
):
    foundry_mock.chat_json_raw.return_value = ("{}", fake_creacion_llm_response())
    foundry_mock.generar_imagen.return_value = b"\x89PNG" + b"\x00" * 100
    imagen_repo_mock.subir_imagen.return_value = "https://fake.blob/x.png"

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    svc.crear_partida(
        Genero.FANTASIA,
        "una arqueóloga escéptica",
        premisa="vengar a su maestro asesinado",
        tono="épico sombrío",
    )

    user_prompt = foundry_mock.chat_json_raw.call_args_list[0][0][1]
    assert "vengar a su maestro asesinado" in user_prompt
    assert "épico sombrío" in user_prompt


def test_avanzar_turno_crea_span_con_atributos(
    foundry_mock, partida_repo_mock, imagen_repo_mock, partida_de_ejemplo, span_exporter
):
    partida_repo_mock.get.return_value = partida_de_ejemplo
    foundry_mock.chat_json_raw.return_value = ("{}", fake_turno_llm_response())

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    svc.avanzar_turno("test-abc-123", "mirar alrededor")

    span = next(s for s in span_exporter.get_finished_spans() if s.name == "avanzar_turno")
    assert span.attributes["codigo_partida"] == "test-abc-123"
    assert span.attributes["prompt_version"] == PROMPT_VERSION


def test_falla_json_incrementa_counter_de_errores(
    foundry_mock, partida_repo_mock, imagen_repo_mock, partida_de_ejemplo, metric_reader
):
    def total_json_errors() -> float:
        return sum(
            p.value
            for p in metric_points(metric_reader, "llm.errors")
            if p.attributes.get("tipo") == "json"
        )

    antes = total_json_errors()
    partida_repo_mock.get.return_value = partida_de_ejemplo
    foundry_mock.chat_json_raw.return_value = ("not json", None)

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    with pytest.raises(RespuestaLLMInvalidaError):
        svc.avanzar_turno("test-abc-123", "mirar")

    assert total_json_errors() > antes


def test_registrar_feedback_marca_el_turno(
    foundry_mock, partida_repo_mock, imagen_repo_mock, partida_de_ejemplo
):
    partida_de_ejemplo.historial.append(
        TurnoHistorial(turno=1, accion_jugador="<inicio>", narrativa="N", opciones=["a", "b", "c"])
    )
    partida_repo_mock.get.return_value = partida_de_ejemplo

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    resultado = svc.registrar_feedback("test-abc-123", 1, incoherente=True)

    assert resultado == "incoherente"
    guardada = partida_repo_mock.upsert.call_args[0][0]
    assert guardada.historial[0].feedback == "incoherente"


def test_registrar_feedback_turno_inexistente(
    foundry_mock, partida_repo_mock, imagen_repo_mock, partida_de_ejemplo
):
    partida_repo_mock.get.return_value = partida_de_ejemplo  # historial vacío

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    with pytest.raises(PartidaNoEncontradaError):
        svc.registrar_feedback("test-abc-123", 99, incoherente=True)


def test_crear_partida_falla_si_llm_no_genera_json_valido_dos_veces(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
):
    foundry_mock.chat_json_raw.return_value = ("not json", None)
    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    with pytest.raises(RespuestaLLMInvalidaError):
        svc.crear_partida(Genero.FANTASIA, "una guerrera valiente")
    assert foundry_mock.chat_json_raw.call_count == 2


def test_avanzar_turno_ok_sin_imagen(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_repo_mock.get.return_value = partida_de_ejemplo
    foundry_mock.chat_json_raw.return_value = ("{}", fake_turno_llm_response())

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    resp = svc.avanzar_turno("test-abc-123", "Acercarme a la vela")

    assert resp.turno == 2
    assert resp.imagen_url is None
    assert resp.estado == EstadoPartida.EN_CURSO
    foundry_mock.generar_imagen.assert_not_called()


def test_avanzar_turno_sin_tirada_una_sola_llamada(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_repo_mock.get.return_value = partida_de_ejemplo
    foundry_mock.chat_json_raw.return_value = ("{}", fake_turno_llm_response())

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    svc.avanzar_turno("test-abc-123", "mirar alrededor")

    assert foundry_mock.chat_json_raw.call_count == 1
    guardada = partida_repo_mock.upsert.call_args[0][0]
    assert guardada.historial[-1].tirada is None


def test_avanzar_turno_con_tirada_hace_dos_llamadas_y_persiste(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_repo_mock.get.return_value = partida_de_ejemplo
    # Fase 1 declara la tirada; fase 2 narra el desenlace (turno completo normal).
    foundry_mock.chat_json_raw.side_effect = [
        ("{}", _fase1_con_tirada(habilidad="destreza", banda="media")),
        ("{}", fake_turno_llm_response()),
    ]

    svc = PartidaService(
        foundry=foundry_mock,
        partidas=partida_repo_mock,
        imagenes=imagen_repo_mock,
        rng=random.Random(123),
    )
    svc.avanzar_turno("test-abc-123", "saltar el abismo")

    assert foundry_mock.chat_json_raw.call_count == 2
    guardada = partida_repo_mock.upsert.call_args[0][0]
    t = guardada.historial[-1].tirada
    assert t is not None

    esperado_d20 = dados.tirar_d20(random.Random(123))
    assert t.habilidad == Habilidad.DESTREZA
    assert t.dc == 15  # banda media
    assert t.modificador == 0  # atributos neutrales (10) → +0
    assert t.d20 == esperado_d20
    assert t.total == esperado_d20
    assert t.resultado == dados.clasificar_tirada(d20=esperado_d20, modificador_total=0, dc=15)


def _tipos_de_eventos_sse(eventos: list[str]) -> list[str]:
    return [e.split("event: ", 1)[1].split("\n", 1)[0] for e in eventos]


def test_stream_con_tirada_emite_evento_tirada_antes_del_turno(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_repo_mock.get.return_value = partida_de_ejemplo
    fase1 = json.dumps(_fase1_con_tirada(habilidad="destreza", banda="media"))
    fase2 = json.dumps(fake_turno_llm_response())

    def _make_gen(payload: str):
        async def gen(_system: str, _user: str):
            yield payload

        return gen

    gens = [_make_gen(fase1), _make_gen(fase2)]
    foundry_mock.chat_streaming_async.side_effect = lambda s, u: gens.pop(0)(s, u)

    svc = PartidaService(
        foundry=foundry_mock,
        partidas=partida_repo_mock,
        imagenes=imagen_repo_mock,
        rng=random.Random(123),
    )

    async def _run() -> list[str]:
        return [e async for e in svc.avanzar_turno_stream("test-abc-123", "saltar el abismo")]

    eventos = asyncio.run(_run())
    tipos = _tipos_de_eventos_sse(eventos)

    # El evento de la tirada llega y precede al evento `turno` (el desenlace).
    assert "tirada" in tipos
    assert tipos.index("tirada") < tipos.index("turno")
    # El turno se entrega atómicamente: no se emiten tokens parciales.
    assert "token" not in tipos
    # Se hicieron las dos llamadas al LLM (fase 1 + fase 2).
    assert foundry_mock.chat_streaming_async.call_count == 2

    # La tirada quedó persistida en el turno.
    guardada = partida_repo_mock.upsert.call_args[0][0]
    assert guardada.historial[-1].tirada is not None
    assert guardada.historial[-1].tirada.dc == 15


def test_stream_fase2_invalida_reintenta_no_streaming_y_no_corta(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    """Si el desenlace streameado viola el schema (p. ej. una opción demasiado
    larga), el servicio reintenta sin streaming y emite el turno igual, sin
    cortar con un evento `error`."""
    partida_repo_mock.get.return_value = partida_de_ejemplo
    fase1 = json.dumps(_fase1_con_tirada(habilidad="destreza", banda="media"))
    # Fase 2 streameada inválida: una opción supera el maxLength de 100.
    fase2_invalida = fake_turno_llm_response()
    fase2_invalida["opciones"] = ["x" * 101, "Opción válida B", "Opción válida C"]

    def _make_gen(payload: str):
        async def gen(_system: str, _user: str):
            yield payload

        return gen

    gens = [_make_gen(fase1), _make_gen(json.dumps(fase2_invalida))]
    foundry_mock.chat_streaming_async.side_effect = lambda s, u: gens.pop(0)(s, u)
    # El reintento no-streaming devuelve un turno válido.
    foundry_mock.chat_json_raw.return_value = ("{}", fake_turno_llm_response())

    svc = PartidaService(
        foundry=foundry_mock,
        partidas=partida_repo_mock,
        imagenes=imagen_repo_mock,
        rng=random.Random(123),
    )

    async def _run() -> list[str]:
        return [e async for e in svc.avanzar_turno_stream("test-abc-123", "saltar el abismo")]

    tipos = _tipos_de_eventos_sse(asyncio.run(_run()))

    # El turno se emitió pese a la fase 2 inválida, y no hubo evento `error`.
    assert "turno" in tipos
    assert "error" not in tipos
    # Se hizo el reintento no-streaming (una llamada a chat_json_raw).
    assert foundry_mock.chat_json_raw.call_count == 1
    # El turno persistido usa las opciones válidas del reintento.
    guardada = partida_repo_mock.upsert.call_args[0][0]
    assert all(len(o) <= 100 for o in guardada.historial[-1].opciones)


def test_stream_sin_tirada_no_emite_evento_tirada(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_repo_mock.get.return_value = partida_de_ejemplo

    async def gen(_system: str, _user: str):
        yield json.dumps(fake_turno_llm_response())

    foundry_mock.chat_streaming_async.side_effect = lambda s, u: gen(s, u)

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )

    async def _run() -> list[str]:
        return [e async for e in svc.avanzar_turno_stream("test-abc-123", "mirar")]

    tipos = _tipos_de_eventos_sse(asyncio.run(_run()))
    assert "tirada" not in tipos
    assert foundry_mock.chat_streaming_async.call_count == 1
    guardada = partida_repo_mock.upsert.call_args[0][0]
    assert guardada.historial[-1].tirada is None


def test_avanzar_turno_normal_no_genera_imagen(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    # Los turnos intermedios ya no generan imagen automáticamente: la pide el jugador.
    partida_de_ejemplo.metadata.turno_actual = 4
    partida_repo_mock.get.return_value = partida_de_ejemplo
    foundry_mock.chat_json_raw.return_value = ("{}", fake_turno_llm_response(necesaria_imagen=True))

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    resp = svc.avanzar_turno("test-abc-123", "Avanzar")

    assert resp.imagen_url is None
    foundry_mock.generar_imagen.assert_not_called()


def test_avanzar_turno_final_genera_imagen(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    # El último turno (finalizada) genera imagen automáticamente.
    partida_repo_mock.get.return_value = partida_de_ejemplo
    foundry_mock.chat_json_raw.return_value = (
        "{}",
        fake_turno_llm_response(estado="finalizada", final="exito"),
    )
    foundry_mock.generar_imagen.return_value = b"\x89PNG" + b"\x00" * 100
    imagen_repo_mock.subir_imagen.return_value = "https://fake.blob/y.png"

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    resp = svc.avanzar_turno("test-abc-123", "Tomar el corazón")

    assert resp.imagen_url == "https://fake.blob/y.png"
    foundry_mock.generar_imagen.assert_called_once()


def test_falla_imagen_no_rompe_turno(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_repo_mock.get.return_value = partida_de_ejemplo
    foundry_mock.chat_json_raw.return_value = (
        "{}",
        fake_turno_llm_response(estado="finalizada", final="exito"),
    )
    foundry_mock.generar_imagen.side_effect = Exception("Timeout")

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    resp = svc.avanzar_turno("test-abc-123", "Avanzar")

    assert resp.turno == 2
    assert resp.imagen_url is None


def test_partida_finalizada_rechaza_nuevos_turnos(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_de_ejemplo.metadata.estado = EstadoPartida.FINALIZADA
    partida_repo_mock.get.return_value = partida_de_ejemplo

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    with pytest.raises(PartidaFinalizadaError):
        svc.avanzar_turno("test-abc-123", "cualquier cosa")


def test_avanzar_turno_finaliza_la_partida(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_repo_mock.get.return_value = partida_de_ejemplo
    foundry_mock.chat_json_raw.return_value = (
        "{}",
        fake_turno_llm_response(estado="finalizada", final="exito"),
    )
    foundry_mock.generar_imagen.return_value = b"\x89PNG" + b"\x00" * 100
    imagen_repo_mock.subir_imagen.return_value = "https://fake.blob/fin.png"

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    resp = svc.avanzar_turno("test-abc-123", "Tomar el corazón")

    assert resp.estado == EstadoPartida.FINALIZADA


def test_turnos_ilimitados(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    # Antes el turno 25 era el tope; ahora no hay límite y el turno avanza normal.
    partida_de_ejemplo.metadata.turno_actual = 999
    partida_repo_mock.get.return_value = partida_de_ejemplo
    foundry_mock.chat_json_raw.return_value = ("{}", fake_turno_llm_response())

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    resp = svc.avanzar_turno("test-abc-123", "Avanzar")

    assert resp.turno == 1000
    assert resp.estado == EstadoPartida.EN_CURSO


def test_avanzar_turno_persiste_arco_y_resumen(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_repo_mock.get.return_value = partida_de_ejemplo
    foundry_mock.chat_json_raw.return_value = (
        "{}",
        fake_turno_llm_response(
            fase_narrativa="climax",
            tension=9,
            resumen_historia="Lyra llegó al corazón de la montaña.",
        ),
    )

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    svc.avanzar_turno("test-abc-123", "Avanzar")

    guardada = partida_repo_mock.upsert.call_args[0][0]
    assert guardada.world_state.fase_narrativa == FaseNarrativa.CLIMAX
    assert guardada.world_state.tension == 9
    assert guardada.world_state.resumen_historia == "Lyra llegó al corazón de la montaña."


def test_user_prompt_incluye_arco_y_resumen_sin_conteo_de_turnos(partida_de_ejemplo):
    partida_de_ejemplo.world_state.fase_narrativa = FaseNarrativa.DESARROLLO
    partida_de_ejemplo.world_state.tension = 6
    partida_de_ejemplo.world_state.resumen_historia = "Resumen previo de prueba."

    prompt = build_turno_user_prompt(partida_de_ejemplo, "mirar alrededor")

    assert "desarrollo" in prompt
    assert "Tensión actual (0-10): 6" in prompt
    assert "Resumen previo de prueba." in prompt
    assert "15-25" not in prompt
    assert "aventura típica" not in prompt


def test_ending_narrativo_finaliza_y_rechaza_proximo_turno(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_repo_mock.get.return_value = partida_de_ejemplo
    foundry_mock.chat_json_raw.return_value = (
        "{}",
        fake_turno_llm_response(estado="finalizada", final="fracaso"),
    )
    foundry_mock.generar_imagen.return_value = b"\x89PNG" + b"\x00" * 100
    imagen_repo_mock.subir_imagen.return_value = "https://fake.blob/fin.png"

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    resp = svc.avanzar_turno("test-abc-123", "Saltar al vacío")

    assert resp.estado == EstadoPartida.FINALIZADA
    assert resp.final == TipoFinal.FRACASO
    assert resp.razon_fin == "Test fin"

    guardada = partida_repo_mock.upsert.call_args[0][0]
    guardada.metadata.estado = EstadoPartida.FINALIZADA
    partida_repo_mock.get.return_value = guardada
    with pytest.raises(PartidaFinalizadaError):
        svc.avanzar_turno("test-abc-123", "Otra acción")


def test_partida_legacy_sin_arco_avanza_con_defaults(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    # Simula un documento previo al cambio: deserializa con los defaults del modelo.
    ws = partida_de_ejemplo.world_state
    assert ws.fase_narrativa == FaseNarrativa.INTRODUCCION
    assert ws.tension == 1
    assert ws.resumen_historia == ""

    partida_repo_mock.get.return_value = partida_de_ejemplo
    foundry_mock.chat_json_raw.return_value = ("{}", fake_turno_llm_response())

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    resp = svc.avanzar_turno("test-abc-123", "Avanzar")

    assert resp.turno == 2


def test_actualizaciones_de_estado_se_aplican(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_repo_mock.get.return_value = partida_de_ejemplo
    respuesta = fake_turno_llm_response()
    respuesta["actualizaciones_estado"]["ubicacion_nueva"] = "Pasillo"
    respuesta["actualizaciones_estado"]["agregar_inventario"] = ["llave"]
    respuesta["actualizaciones_estado"]["evento_clave"] = "Tomó la llave"
    foundry_mock.chat_json_raw.return_value = ("{}", respuesta)

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    svc.avanzar_turno("test-abc-123", "Tomar la llave")

    guardada = partida_repo_mock.upsert.call_args[0][0]
    assert guardada.world_state.ubicacion_actual == "Pasillo"
    assert "llave" in guardada.personaje.inventario
    assert "Tomó la llave" in guardada.world_state.eventos_clave


def test_reintento_con_prompt_correctivo(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_repo_mock.get.return_value = partida_de_ejemplo
    foundry_mock.chat_json_raw.side_effect = [
        ("no json", None),
        ("{}", fake_turno_llm_response()),
    ]

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    resp = svc.avanzar_turno("test-abc-123", "Avanzar")
    assert resp.turno == 2
    assert foundry_mock.chat_json_raw.call_count == 2


def _turno_con_escena(turno: int, imagen_url: str | None = None) -> TurnoHistorial:
    return TurnoHistorial(
        turno=turno,
        accion_jugador="Avanzar",
        narrativa="Narrativa de prueba para el turno.",
        opciones=["A", "B", "C"],
        imagen_url=imagen_url,
        descripcion_escena_en="A dim chamber with carved stone walls",
    )


def test_generar_imagen_turno_ok(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_de_ejemplo.historial = [_turno_con_escena(2)]
    partida_repo_mock.get.return_value = partida_de_ejemplo
    foundry_mock.generar_imagen.return_value = b"\x89PNG" + b"\x00" * 100
    imagen_repo_mock.subir_imagen.return_value = "https://fake.blob/z.png"

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    url = svc.generar_imagen_turno("test-abc-123", 2)

    assert url == "https://fake.blob/z.png"
    assert partida_de_ejemplo.historial[0].imagen_url == "https://fake.blob/z.png"
    assert partida_de_ejemplo.metadata.imagenes_generadas == 1
    partida_repo_mock.upsert.assert_called_once()


def test_generar_imagen_turno_idempotente_si_ya_tiene(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_de_ejemplo.historial = [_turno_con_escena(2, imagen_url="https://fake.blob/ya.png")]
    partida_repo_mock.get.return_value = partida_de_ejemplo

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    url = svc.generar_imagen_turno("test-abc-123", 2)

    assert url == "https://fake.blob/ya.png"
    foundry_mock.generar_imagen.assert_not_called()
    partida_repo_mock.upsert.assert_not_called()


def test_generar_imagen_turno_limite_excedido(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_de_ejemplo.metadata.imagenes_generadas = 25
    partida_de_ejemplo.historial = [_turno_con_escena(2)]
    partida_repo_mock.get.return_value = partida_de_ejemplo

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    with pytest.raises(LimiteImagenesExcedidoError):
        svc.generar_imagen_turno("test-abc-123", 2)
    foundry_mock.generar_imagen.assert_not_called()


def test_generar_imagen_turno_inexistente(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_de_ejemplo.historial = [_turno_con_escena(2)]
    partida_repo_mock.get.return_value = partida_de_ejemplo

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    with pytest.raises(PartidaNoEncontradaError):
        svc.generar_imagen_turno("test-abc-123", 99)


def test_generar_imagen_turno_sin_descripcion(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    turno = _turno_con_escena(2)
    turno.descripcion_escena_en = None
    partida_de_ejemplo.historial = [turno]
    partida_repo_mock.get.return_value = partida_de_ejemplo

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    with pytest.raises(RespuestaLLMInvalidaError):
        svc.generar_imagen_turno("test-abc-123", 2)


def test_generar_imagen_turno_falla_foundry(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_de_ejemplo.historial = [_turno_con_escena(2)]
    partida_repo_mock.get.return_value = partida_de_ejemplo
    foundry_mock.generar_imagen.side_effect = Exception("Timeout")

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    with pytest.raises(FoundryError):
        svc.generar_imagen_turno("test-abc-123", 2)


# --- Referencia visual del personaje (flujo de imagen anclada) ---------------


def test_primera_imagen_genera_referencia_no_cuenta_al_cupo_y_escena_via_edit(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_de_ejemplo.metadata.usa_referencia_visual = True
    partida_de_ejemplo.historial = [_turno_con_escena(2)]
    partida_repo_mock.get.return_value = partida_de_ejemplo
    foundry_mock.generar_imagen.return_value = b"REF"  # referencia
    foundry_mock.editar_imagen.return_value = b"SCENE"  # escena
    imagen_repo_mock.subir_referencia.return_value = "https://fake.blob/ref.jpg"
    imagen_repo_mock.subir_imagen.return_value = "https://fake.blob/scene.png"

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    url = svc.generar_imagen_turno("test-abc-123", 2)

    assert url == "https://fake.blob/scene.png"
    # La referencia se generó una vez (generar_imagen) y la escena vía edit.
    foundry_mock.generar_imagen.assert_called_once()
    foundry_mock.editar_imagen.assert_called_once()
    # La referencia se guardó en el personaje.
    assert partida_de_ejemplo.personaje.referencia_visual_url == "https://fake.blob/ref.jpg"
    # Solo la escena cuenta contra el cupo; la referencia no.
    assert partida_de_ejemplo.metadata.imagenes_generadas == 1


def test_segunda_imagen_reusa_la_referencia_sin_regenerarla(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_de_ejemplo.metadata.usa_referencia_visual = True
    partida_de_ejemplo.personaje.referencia_visual_url = "https://fake.blob/ref.jpg"
    partida_de_ejemplo.historial = [_turno_con_escena(2)]
    partida_repo_mock.get.return_value = partida_de_ejemplo
    imagen_repo_mock.descargar_imagen.return_value = b"REF"
    foundry_mock.editar_imagen.return_value = b"SCENE"
    imagen_repo_mock.subir_imagen.return_value = "https://fake.blob/scene.png"

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    url = svc.generar_imagen_turno("test-abc-123", 2)

    assert url == "https://fake.blob/scene.png"
    foundry_mock.generar_imagen.assert_not_called()  # no se regenera la referencia
    imagen_repo_mock.descargar_imagen.assert_called_once_with("https://fake.blob/ref.jpg")
    foundry_mock.editar_imagen.assert_called_once()
    assert partida_de_ejemplo.metadata.imagenes_generadas == 1


def test_falla_referencia_degrada_a_imagen_por_texto(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_de_ejemplo.metadata.usa_referencia_visual = True
    partida_de_ejemplo.historial = [_turno_con_escena(2)]
    partida_repo_mock.get.return_value = partida_de_ejemplo

    # generar_imagen falla SOLO para el prompt de referencia; el fallback por
    # texto (escena) usa el mismo método y debe funcionar.
    def fake_generar(prompt):
        if _es_prompt_de_referencia(prompt):
            raise Exception("ref boom")
        return b"SCENE_TEXT"

    foundry_mock.generar_imagen.side_effect = fake_generar
    imagen_repo_mock.subir_imagen.return_value = "https://fake.blob/scene.png"

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    url = svc.generar_imagen_turno("test-abc-123", 2)

    assert url == "https://fake.blob/scene.png"
    # La escena se generó por texto, no por edit.
    foundry_mock.editar_imagen.assert_not_called()
    # La referencia quedó sin setear → se reintenta en la próxima llamada.
    assert partida_de_ejemplo.personaje.referencia_visual_url is None


def test_chokepoint_en_cupo_no_genera_referencia_ni_escena(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_de_ejemplo.metadata.usa_referencia_visual = True

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    res = svc._generar_imagen_segura(
        codigo_partida="test-abc-123",
        turno=1,
        personaje=partida_de_ejemplo.personaje,
        descripcion_escena_en="A dim chamber",
        genero=Genero.FANTASIA,
        imagenes_previas=25,
        usa_referencia=True,
    )

    assert res is None
    foundry_mock.generar_imagen.assert_not_called()
    foundry_mock.editar_imagen.assert_not_called()
    assert partida_de_ejemplo.personaje.referencia_visual_url is None


# --- resolver_npcs_visuales (helper de anclaje de NPCs) ----------------------


def _npc(nombre: str, visual: str | None) -> NPC:
    return NPC(
        nombre=nombre, descripcion="x", actitud=Actitud.NEUTRAL, descripcion_visual_en=visual
    )


def test_resolver_npcs_visuales_vacio_devuelve_vacio():
    assert resolver_npcs_visuales([], [_npc("Eldrin", "old hermit")]) == []


def test_resolver_npcs_visuales_match_tolerante():
    npcs = [_npc("Gorad el Carcelero", "bald jailer, rusted keys")]
    # Distinta capitalización y espacios sobrantes igual resuelven.
    out = resolver_npcs_visuales(["  gorad EL carcelero "], npcs)
    assert out == ["bald jailer, rusted keys"]


def test_resolver_npcs_visuales_ignora_nombre_alucinado():
    npcs = [_npc("Eldrin", "old hermit")]
    assert resolver_npcs_visuales(["Nadie"], npcs) == []


def test_resolver_npcs_visuales_ignora_npc_sin_descripcion():
    npcs = [_npc("Eldrin", None)]
    assert resolver_npcs_visuales(["Eldrin"], npcs) == []


def test_resolver_npcs_visuales_respeta_el_tope():
    from app.services.prompts import MAX_NPCS_ANCLADOS

    npcs = [_npc(f"NPC{i}", f"visual {i}") for i in range(MAX_NPCS_ANCLADOS + 2)]
    nombres = [n.nombre for n in npcs]
    out = resolver_npcs_visuales(nombres, npcs)
    assert len(out) == MAX_NPCS_ANCLADOS


# --- consistencia visual de NPCs en el servicio ------------------------------


def _turno_con_npc(visual: str) -> dict:
    payload = fake_turno_llm_response()
    payload["actualizaciones_estado"]["npc_encontrado"] = {
        "nombre": "Gorad",
        "descripcion": "Un carcelero hostil",
        "actitud": "hostil",
        "descripcion_visual_en": visual,
    }
    return payload


def test_avanzar_turno_persiste_descripcion_visual_del_npc(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_repo_mock.get.return_value = partida_de_ejemplo
    visual = "Bald jailer, grey beard, rusted iron keys at the belt"
    foundry_mock.chat_json_raw.return_value = ("{}", _turno_con_npc(visual))

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    svc.avanzar_turno("test-abc-123", "Hablar con el carcelero")

    guardada = partida_repo_mock.upsert.call_args[0][0]
    npc = next(n for n in guardada.world_state.npcs if n.nombre == "Gorad")
    assert npc.descripcion_visual_en == visual


def test_avanzar_turno_final_ancla_npc_presente_en_el_prompt(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    # NPC ya conocido con visual canónica; el turno final lo declara presente.
    visual = "Bald jailer, grey beard, rusted iron keys"
    partida_de_ejemplo.world_state.npcs = [_npc("Gorad", visual)]
    partida_repo_mock.get.return_value = partida_de_ejemplo

    payload = fake_turno_llm_response(estado="finalizada", final="exito")
    payload["generar_imagen"]["npcs_en_escena"] = ["Gorad"]
    foundry_mock.chat_json_raw.return_value = ("{}", payload)
    foundry_mock.generar_imagen.return_value = b"\x89PNG" + b"\x00" * 100
    imagen_repo_mock.subir_imagen.return_value = "https://fake.blob/scene.png"

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    svc.avanzar_turno("test-abc-123", "Enfrentar al carcelero")

    prompt = foundry_mock.generar_imagen.call_args[0][0]
    assert "Also present:" in prompt
    assert visual in prompt


def test_generar_imagen_turno_ancla_npc_guardado_en_el_turno(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    # On-demand: el turno guardó npcs_en_escena; se resuelve contra el estado actual.
    visual = "Bald jailer, grey beard, rusted iron keys"
    partida_de_ejemplo.world_state.npcs = [_npc("Gorad", visual)]
    turno = _turno_con_escena(2)
    turno.npcs_en_escena = ["Gorad"]
    partida_de_ejemplo.historial = [turno]
    partida_repo_mock.get.return_value = partida_de_ejemplo
    foundry_mock.generar_imagen.return_value = b"\x89PNG" + b"\x00" * 100
    imagen_repo_mock.subir_imagen.return_value = "https://fake.blob/z.png"

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    svc.generar_imagen_turno("test-abc-123", 2)

    prompt = foundry_mock.generar_imagen.call_args[0][0]
    assert visual in prompt


def test_stream_final_ancla_npc_presente_en_el_prompt(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    visual = "Bald jailer, grey beard, rusted iron keys"
    partida_de_ejemplo.world_state.npcs = [_npc("Gorad", visual)]
    partida_repo_mock.get.return_value = partida_de_ejemplo

    payload = fake_turno_llm_response(estado="finalizada", final="exito")
    payload["generar_imagen"]["npcs_en_escena"] = ["Gorad"]

    async def gen(_system: str, _user: str):
        yield json.dumps(payload)

    foundry_mock.chat_streaming_async.side_effect = lambda s, u: gen(s, u)
    foundry_mock.generar_imagen.return_value = b"\x89PNG" + b"\x00" * 100
    imagen_repo_mock.subir_imagen.return_value = "https://fake.blob/scene.png"

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )

    async def _run() -> list[str]:
        return [e async for e in svc.avanzar_turno_stream("test-abc-123", "Enfrentar al carcelero")]

    asyncio.run(_run())

    prompt = foundry_mock.generar_imagen.call_args[0][0]
    assert visual in prompt
