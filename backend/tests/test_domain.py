"""Tests de los modelos de dominio relacionados a la creación de partidas."""

import pytest
from pydantic import ValidationError

from app.models.domain import (
    Genero,
    MetadataPartida,
    PartidaResumen,
    Personaje,
    StartPartidaRequest,
)


def _resumen_kwargs(**extra) -> dict:
    base = {
        "codigo_partida": "abc-123",
        "nombre_personaje": "Lyra",
        "turno_actual": 3,
        "estado": "en_curso",
        "genero": "fantasía",
        "creada_en": "2026-06-16T00:00:00Z",
    }
    base.update(extra)
    return base


# --- StartPartidaRequest -----------------------------------------------------


def test_start_request_acepta_premisa_y_tono_opcionales():
    req = StartPartidaRequest(
        genero=Genero.FANTASIA,
        descripcion_personaje="una herrera huérfana",
        premisa="vengar a su maestro",
        tono="épico sombrío",
    )
    assert req.premisa == "vengar a su maestro"
    assert req.tono == "épico sombrío"


def test_start_request_premisa_y_tono_default_none():
    req = StartPartidaRequest(genero=Genero.FANTASIA, descripcion_personaje="una herrera huérfana")
    assert req.premisa is None
    assert req.tono is None


def test_start_request_rechaza_premisa_demasiado_larga():
    with pytest.raises(ValidationError):
        StartPartidaRequest(
            genero=Genero.FANTASIA,
            descripcion_personaje="una herrera huérfana",
            premisa="x" * 201,
        )


def test_start_request_rechaza_tono_demasiado_largo():
    with pytest.raises(ValidationError):
        StartPartidaRequest(
            genero=Genero.FANTASIA,
            descripcion_personaje="una herrera huérfana",
            tono="x" * 101,
        )


def test_start_request_sigue_requiriendo_descripcion():
    with pytest.raises(ValidationError):
        StartPartidaRequest(genero=Genero.FANTASIA, descripcion_personaje="abc")


# --- PartidaResumen.prompt_version ------------------------------------------


def test_resumen_expone_prompt_version():
    r = PartidaResumen.model_validate(_resumen_kwargs(prompt_version="2.1.0"))
    assert r.prompt_version == "2.1.0"


def test_resumen_normaliza_prompt_version_nula_a_1_0_0():
    r = PartidaResumen.model_validate(_resumen_kwargs(prompt_version=None))
    assert r.prompt_version == "1.0.0"


def test_resumen_normaliza_prompt_version_ausente_a_1_0_0():
    r = PartidaResumen.model_validate(_resumen_kwargs())
    assert r.prompt_version == "1.0.0"


# --- Referencia visual del personaje (partidas previas = defaults seguros) ---


def test_personaje_legacy_sin_referencia_visual_default_none():
    # Documento previo al cambio: sin el campo, deserializa como None.
    pj = Personaje.model_validate(
        {
            "nombre": "Lyra",
            "descripcion_narrativa": "Arqueóloga escéptica.",
            "descripcion_visual_en": "Woman around 40, dark hair.",
        }
    )
    assert pj.referencia_visual_url is None


def test_metadata_legacy_sin_flag_referencia_default_false():
    # Documento previo al cambio: sin el campo, queda en el flujo por texto.
    meta = MetadataPartida.model_validate(
        {"genero": "fantasía", "creada_en": "2026-06-16T00:00:00Z"}
    )
    assert meta.usa_referencia_visual is False
