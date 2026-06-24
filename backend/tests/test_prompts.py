"""Tests de seeds creativas y armado del prompt de creación."""

import random

import pytest

from app.models.domain import Genero
from app.services.prompts import (
    CREATION_POOLS,
    ESTILO_POR_GENERO,
    MAX_NPCS_ANCLADOS,
    PROMPT_VERSION,
    SYSTEM_PROMPT_CREACION,
    SYSTEM_PROMPT_RESOLUCION,
    SYSTEM_PROMPT_TURNO,
    SemillaCreativa,
    build_creacion_user_prompt,
    build_image_prompt,
    build_reference_prompt,
    sample_seed,
)

TODOS_LOS_GENEROS = list(Genero)


# --- sample_seed -------------------------------------------------------------


@pytest.mark.parametrize("genero", TODOS_LOS_GENEROS)
def test_sample_seed_es_determinista_con_rng_sembrado(genero):
    a = sample_seed(genero, random.Random(42))
    b = sample_seed(genero, random.Random(42))
    assert a == b


@pytest.mark.parametrize("genero", TODOS_LOS_GENEROS)
def test_sample_seed_devuelve_valores_de_los_pools(genero):
    seed = sample_seed(genero, random.Random(7))
    pools = CREATION_POOLS[genero]
    assert seed.nombre in pools["nombres"]
    assert seed.premisa in pools["premisas"]
    assert seed.tono in pools["tonos"]
    assert seed.apertura in pools["aperturas"]


@pytest.mark.parametrize("genero", TODOS_LOS_GENEROS)
def test_sample_seed_completa_todas_las_dimensiones(genero):
    seed = sample_seed(genero)
    assert isinstance(seed, SemillaCreativa)
    assert seed.nombre and seed.premisa and seed.tono and seed.apertura


# --- build_creacion_user_prompt ---------------------------------------------


def _seed_fija() -> SemillaCreativa:
    return SemillaCreativa(
        nombre="SEED_NOMBRE",
        premisa="SEED_PREMISA",
        tono="SEED_TONO",
        apertura="SEED_APERTURA",
    )


def test_prompt_usa_seed_como_inspiracion_sin_input_jugador():
    prompt = build_creacion_user_prompt(Genero.FANTASIA, "una herrera huérfana", _seed_fija())
    assert "SEMILLA CREATIVA" in prompt
    assert "SEED_PREMISA" in prompt
    assert "SEED_TONO" in prompt
    assert "SEED_APERTURA" in prompt


def test_prompt_honra_premisa_del_jugador_y_descarta_la_de_la_seed():
    prompt = build_creacion_user_prompt(
        Genero.FANTASIA,
        "una herrera huérfana",
        _seed_fija(),
        premisa="vengar a su maestro asesinado",
    )
    assert "vengar a su maestro asesinado" in prompt
    # La premisa del jugador se honra; la de la seed no debe aparecer.
    assert "SEED_PREMISA" not in prompt
    # Pero el tono de la seed sí (el jugador no lo dio).
    assert "SEED_TONO" in prompt


def test_prompt_honra_tono_del_jugador_y_descarta_el_de_la_seed():
    prompt = build_creacion_user_prompt(
        Genero.TERROR,
        "un faro",
        _seed_fija(),
        tono="opresivo y húmedo",
    )
    assert "opresivo y húmedo" in prompt
    assert "SEED_TONO" not in prompt
    assert "SEED_PREMISA" in prompt


def test_prompt_marca_seccion_de_input_del_jugador_cuando_lo_hay():
    prompt = build_creacion_user_prompt(
        Genero.FANTASIA,
        "una herrera",
        _seed_fija(),
        premisa="encontrar a su hermana",
    )
    assert "JUGADOR" in prompt


def test_prompt_incluye_precedencia_de_nombre():
    prompt = build_creacion_user_prompt(Genero.FANTASIA, "una herrera", _seed_fija())
    # El nombre de la seed es solo respaldo; el del jugador (si lo da) manda.
    assert "respaldo" in prompt.lower()
    assert "SEED_NOMBRE" in prompt


# --- build_reference_prompt --------------------------------------------------


def test_reference_prompt_incluye_visual_estilo_y_encuadre_sin_escena():
    visual = "Woman around 40, dark brown wavy hair, olive canvas field jacket"
    prompt = build_reference_prompt(visual, Genero.FANTASIA)

    # Incluye la descripción visual del personaje y el estilo del género.
    assert visual in prompt
    assert ESTILO_POR_GENERO[Genero.FANTASIA] in prompt

    low = prompt.lower()
    # Encuadre de ficha de referencia: cuerpo entero, fondo neutro, un solo
    # sujeto, sin texto.
    assert "full-body" in low
    assert "neutral" in low and "background" in low
    assert "single" in low
    assert "no text" in low

    # NO debe contener una descripción de escena (eso lo aporta el edit por turno).
    assert "scene:" not in low


# --- regla de idioma (español rioplatense salvo `_en`) -----------------------


@pytest.mark.parametrize(
    "prompt",
    [
        pytest.param(SYSTEM_PROMPT_TURNO, id="turno"),
        pytest.param(SYSTEM_PROMPT_CREACION, id="creacion"),
    ],
)
def test_system_prompt_fija_regla_de_idioma_bidireccional(prompt: str):
    """Ambos system prompts deben fijar explícitamente que todo el texto va en
    español rioplatense salvo los campos `_en`, que van en inglés. Esta es la
    palanca que evita que objetivo/inventario/opciones fuguen al inglés."""
    low = prompt.lower()
    assert "español rioplatense" in low
    # La regla se ancla a la convención `_en` de forma explícita.
    assert "_en" in prompt
    # Y nombra inglés como la excepción (no como el default).
    assert "inglés" in low


def test_prompt_version_fue_bumpeada():
    """Pin de la versión activa: cambiar prompts/schema sin bumpear esto (y sin
    agregar fila al changelog en docs/prompts.md) rompe este test a propósito."""
    assert PROMPT_VERSION == "3.4.0"


# --- build_image_prompt: anclaje visual de NPCs ------------------------------

_VISUAL_PJ = "Woman around 30, red braided hair, leather armor"
_ESCENA = "a torchlit dungeon chamber with wet stone walls"


def test_build_image_prompt_incluye_npcs_presentes():
    npc1 = "Old jailer, bald, grey beard, rusted iron keys"
    npc2 = "Young thief, hooded, green cloak"
    prompt = build_image_prompt(_VISUAL_PJ, _ESCENA, Genero.FANTASIA, npcs_visuales_en=[npc1, npc2])
    assert "Also present:" in prompt
    assert npc1 in prompt and npc2 in prompt
    # El protagonista y la escena siguen presentes.
    assert _VISUAL_PJ in prompt
    assert _ESCENA in prompt


def test_build_image_prompt_sin_npcs_equivale_al_actual():
    """Sin NPCs el prompt no debe ganar la sección 'Also present'."""
    base = build_image_prompt(_VISUAL_PJ, _ESCENA, Genero.FANTASIA)
    con_lista_vacia = build_image_prompt(_VISUAL_PJ, _ESCENA, Genero.FANTASIA, npcs_visuales_en=[])
    con_none = build_image_prompt(_VISUAL_PJ, _ESCENA, Genero.FANTASIA, npcs_visuales_en=None)
    assert "Also present" not in base
    assert base == con_lista_vacia == con_none


# --- system prompts: consistencia visual de NPCs -----------------------------


@pytest.mark.parametrize(
    "prompt",
    [
        pytest.param(SYSTEM_PROMPT_TURNO, id="turno"),
        pytest.param(SYSTEM_PROMPT_RESOLUCION, id="resolucion"),
    ],
)
def test_system_prompt_pide_visual_de_npc_y_presencia(prompt: str):
    low = prompt.lower()
    assert "descripcion_visual_en" in low
    assert "npcs_en_escena" in low


def test_max_npcs_anclados_es_positivo():
    assert MAX_NPCS_ANCLADOS >= 1


# --- tiradas: system prompt del turno y prompt de resolución (fase 2) --------


def test_system_prompt_turno_explica_cuando_pedir_tirada():
    low = SYSTEM_PROMPT_TURNO.lower()
    assert "requiere_tirada" in low
    # Nombra las seis habilidades y la decisión trivial/imposible = sin tirada.
    assert "fuerza" in low and "carisma" in low
    assert "trivial" in low and "imposible" in low


def test_build_resolucion_user_prompt_inyecta_la_tirada(partida_de_ejemplo):
    from app.models.domain import Banda, Habilidad, ResultadoTirada, Tirada
    from app.services.prompts import SYSTEM_PROMPT_RESOLUCION, build_resolucion_user_prompt

    tirada = Tirada(
        habilidad=Habilidad.DESTREZA,
        banda=Banda.MEDIA,
        dc=15,
        d20=11,
        modificador=4,
        total=15,
        resultado=ResultadoTirada.EXITO,
    )
    prompt = build_resolucion_user_prompt(partida_de_ejemplo, "saltar el abismo", tirada)

    assert "destreza" in prompt
    assert "DC 15" in prompt
    assert "exito" in prompt
    assert "+4" in prompt
    # El system prompt de resolución obliga a honrar el resultado.
    assert "honr" in SYSTEM_PROMPT_RESOLUCION.lower()
