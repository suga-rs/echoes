"""Tests del PartidaService con todas las dependencias mockeadas."""

import pytest

from app.core.exceptions import (
    FoundryError,
    LimiteImagenesExcedido,
    LimiteTurnosExcedido,
    PartidaFinalizada,
    PartidaNoEncontrada,
    RespuestaLLMInvalida,
)
from app.models.domain import EstadoPartida, Genero, TurnoHistorial
from app.services.partida_service import PartidaService


def fake_turno_llm_response(
    *,
    necesaria_imagen: bool = False,
    estado: str = "en_curso",
    final: str | None = None,
) -> dict:
    return {
        "narrativa": (
            "Avanzás por el pasillo oscuro. El aire huele a humedad. "
            "Una vela parpadea al fondo, dibujando sombras en las paredes."
        ),
        "opciones": [
            "Acercarme a la vela con cautela",
            "Llamar para ver si alguien responde",
            "Regresar a la entrada",
        ],
        "actualizaciones_estado": {
            "ubicacion_nueva": None,
            "agregar_inventario": [],
            "quitar_inventario": [],
            "evento_clave": None,
            "npc_encontrado": None,
            "npc_actitud_cambio": None,
            "pista_descubierta": None,
        },
        "generar_imagen": {
            "necesaria": necesaria_imagen,
            "descripcion_escena_en": "A dark corridor lit by a flickering candle",
        },
        "estado_aventura": {
            "tipo": estado,
            "final": final,
            "razon_fin": "Test fin" if final else None,
        },
    }


def fake_creacion_llm_response() -> dict:
    return {
        "personaje": {
            "nombre": "Lyra",
            "descripcion_narrativa": "Arqueóloga escéptica de 40 años.",
            "descripcion_visual_en": (
                "Woman around 40, Mediterranean features, dark brown wavy hair to "
                "shoulders, hazel eyes, athletic build. Olive canvas field jacket "
                "with leather elbow patches, khaki cargo pants, brown leather boots."
            ),
            "inventario_inicial": ["linterna", "diario"],
        },
        "world_state_inicial": {
            "ubicacion_inicial": "Entrada de la cripta",
            "objetivo": "Encontrar el corazón de la montaña",
        },
        "primera_escena": {
            "narrativa": (
                "Descendés los escalones de piedra. El aire se vuelve denso. "
                "Al fondo, una luz tenue."
            ),
            "opciones": ["Encender la linterna", "Avanzar en silencio", "Llamar"],
            "descripcion_imagen_en": "Stone staircase descending into a dark crypt",
        },
    }


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


def test_crear_partida_falla_si_llm_no_genera_json_valido_dos_veces(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
):
    foundry_mock.chat_json_raw.return_value = ("not json", None)
    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    with pytest.raises(RespuestaLLMInvalida):
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
    with pytest.raises(PartidaFinalizada):
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


def test_limite_turnos_excedido(
    foundry_mock,
    partida_repo_mock,
    imagen_repo_mock,
    partida_de_ejemplo,
):
    partida_de_ejemplo.metadata.turno_actual = 25
    partida_repo_mock.get.return_value = partida_de_ejemplo

    svc = PartidaService(
        foundry=foundry_mock, partidas=partida_repo_mock, imagenes=imagen_repo_mock
    )
    with pytest.raises(LimiteTurnosExcedido):
        svc.avanzar_turno("test-abc-123", "Avanzar")


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
    with pytest.raises(LimiteImagenesExcedido):
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
    with pytest.raises(PartidaNoEncontrada):
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
    with pytest.raises(RespuestaLLMInvalida):
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
