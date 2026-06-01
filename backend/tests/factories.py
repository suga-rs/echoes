"""Builders de payloads válidos del LLM, compartidos entre tests.

Se importan como `from factories import ...` (tests/ está en pythonpath).
Cada builder devuelve un dict válido contra su schema, base para mutar en tests.
"""


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
