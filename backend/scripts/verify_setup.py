"""Verificación de setup. Probar conectividad real a Foundry, Cosmos, Blob."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import UTC

from app.core.config import get_settings
from app.repositories.imagen_repo import ImagenRepository
from app.repositories.partida_repo import PartidaRepository
from app.services.foundry_client import FoundryClient


def check(nombre: str, fn) -> bool:
    print(f"  {nombre}...", end=" ", flush=True)
    try:
        fn()
    except Exception as e:
        print(f"FALLO\n      {type(e).__name__}: {e}")
        return False
    print("OK")
    return True


def main() -> int:
    print("\n=== Verificación de setup ===\n")
    settings = get_settings()
    print(f"Foundry endpoint: {settings.foundry_endpoint}")
    print(f"Auth: {'Entra ID' if settings.use_entra_id else 'API key'}\n")

    foundry = FoundryClient(settings)
    partidas = PartidaRepository(settings)
    imagenes = ImagenRepository(settings)

    ok = True

    def test_llm():
        resp = foundry.chat_json(
            system_prompt='Respondé solo con JSON valido: {"ok": true}. Nada más.',
            user_prompt="ping",
            max_tokens=20,
        )
        assert "ok" in resp

    def test_image():
        png = foundry.generar_imagen(
            "A simple red apple on a plain white background, minimalist",
            size="1024x1024",
        )
        assert isinstance(png, bytes) and len(png) > 1000

    def test_cosmos():
        from datetime import datetime

        from app.models.domain import (
            EstadoPartida,
            Genero,
            MetadataPartida,
            Partida,
            Personaje,
            WorldState,
        )

        codigo = "verify-test-zzz"
        partida = Partida(
            id=codigo,
            codigo_partida=codigo,
            metadata=MetadataPartida(
                genero=Genero.FANTASIA,
                creada_en=datetime.now(UTC),
                estado=EstadoPartida.EN_CURSO,
            ),
            personaje=Personaje(
                nombre="Test",
                descripcion_narrativa="Test character",
                descripcion_visual_en="Test visual description for verification only",
            ),
            world_state=WorldState(ubicacion_actual="test", objetivo="verify"),
        )
        partidas.upsert(partida)
        recovered = partidas.get(codigo)
        assert recovered.codigo_partida == codigo
        partidas._container.delete_item(item=codigo, partition_key=codigo)

    def test_blob():
        url = imagenes.subir_imagen("verify-test", 0, b"PNG dummy")
        assert url.startswith("https://")

    print("Probando servicios:")
    ok &= check("Foundry / gpt-4.1-mini (chat_json)", test_llm)
    ok &= check("Foundry / gpt-image-2 (generar_imagen)", test_image)
    ok &= check("Cosmos DB (upsert + get + delete)", test_cosmos)
    ok &= check("Blob Storage (subir_imagen)", test_blob)

    print()
    if ok:
        print("Todo OK. Podés levantar: uvicorn app.main:app --reload")
        return 0
    else:
        print("Hay servicios con falla. Revisar .env y permisos.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
