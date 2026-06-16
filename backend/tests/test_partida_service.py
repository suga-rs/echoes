"""Tests del PartidaService con todas las dependencias mockeadas."""

import pytest
from factories import fake_creacion_llm_response, fake_turno_llm_response, metric_points

from app.core.exceptions import (
    FoundryError,
    LimiteImagenesExcedidoError,
    PartidaFinalizadaError,
    PartidaNoEncontradaError,
    RespuestaLLMInvalidaError,
)
from app.models.domain import EstadoPartida, FaseNarrativa, Genero, TipoFinal, TurnoHistorial
from app.services.partida_service import PartidaService
from app.services.prompts import PROMPT_VERSION, build_turno_user_prompt


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
