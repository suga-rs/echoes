"""Remediación one-off: traduce a español rioplatense los campos cortos que
fugaban al inglés (`objetivo` del world state e `inventario` del personaje) en
partidas creadas antes de la regla de idioma (PROMPT_VERSION 2.2.0).

Es idempotente: usa una llamada "traducir si hace falta" que devuelve verbatim
el texto que ya está en español, así que correrlo de nuevo no cambia nada. Solo
toca `world_state.objetivo` y `personaje.inventario`; deja intactos los campos
`_en`, el historial y todo el resto del estado.

Uso (desde backend/, con el venv activo y el .env configurado):

    python -m scripts.remediar_idioma            # dry-run: solo reporta
    python -m scripts.remediar_idioma --write     # persiste los cambios
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.domain import Partida
from app.repositories.partida_repo import PartidaRepository
from app.services.foundry_client import FoundryClient

SYSTEM_TRADUCCION = """\
Sos un traductor al español rioplatense (es-AR). Recibís un JSON con un array \
`textos` (frases cortas: un objetivo de aventura y nombres de objetos de \
inventario). Devolvés SOLO un JSON con un array `textos` del MISMO largo y en \
el MISMO orden, con cada texto en español rioplatense.

Reglas:
- Si un texto YA está en español, devolvelo TAL CUAL, sin cambios.
- Traducí solo lo que esté en inglés (u otro idioma).
- No agregues, quites ni reordenes elementos. Mismo largo, mismo orden.
- Usá "vos" y conjugaciones rioplatenses cuando aplique.
- Nada de texto fuera del JSON.
"""


def traducir_si_hace_falta(textos: list[str], foundry: FoundryClient) -> list[str]:
    """Devuelve cada texto en español rioplatense, verbatim si ya lo estaba.
    Lanza ValueError si el LLM no respeta el largo/orden (no aplicamos cambios
    parciales que podrían desalinear objetivo e inventario)."""
    if not textos:
        return []
    user = json.dumps({"textos": textos}, ensure_ascii=False)
    payload = foundry.chat_json(SYSTEM_TRADUCCION, user, temperature=0.0)
    traducidos = payload.get("textos")
    if not isinstance(traducidos, list) or len(traducidos) != len(textos):
        raise ValueError(
            f"Traducción inválida: se esperaban {len(textos)} textos, se recibió {traducidos!r}"
        )
    return [str(t) for t in traducidos]


def remediar_partida(partida: Partida, foundry: FoundryClient) -> bool:
    """Traduce objetivo e inventario in-place. Devuelve True si algo cambió.
    No toca ningún otro campo de la partida."""
    originales = [partida.world_state.objetivo, *partida.personaje.inventario]
    traducidos = traducir_si_hace_falta(originales, foundry)

    nuevo_objetivo = traducidos[0]
    nuevo_inventario = traducidos[1:]

    cambio = (
        nuevo_objetivo != partida.world_state.objetivo
        or nuevo_inventario != partida.personaje.inventario
    )
    partida.world_state.objetivo = nuevo_objetivo
    partida.personaje.inventario = nuevo_inventario
    return cambio


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Persiste los cambios. Sin esta bandera corre en dry-run (solo reporta).",
    )
    args = parser.parse_args()
    modo = "WRITE" if args.write else "DRY-RUN"

    foundry = FoundryClient()
    repo = PartidaRepository()

    resumenes = repo.list_all()
    print(f"\n=== Remediación de idioma ({modo}) — {len(resumenes)} partidas ===\n")

    revisadas = cambiadas = errores = 0
    for resumen in resumenes:
        codigo = resumen.codigo_partida
        try:
            partida = repo.get(codigo)
            antes_obj = partida.world_state.objetivo
            antes_inv = list(partida.personaje.inventario)
            cambio = remediar_partida(partida, foundry)
            revisadas += 1
            if cambio:
                cambiadas += 1
                print(f"[cambia] {codigo}")
                print(f"    objetivo:   {antes_obj!r} -> {partida.world_state.objetivo!r}")
                if antes_inv != partida.personaje.inventario:
                    print(f"    inventario: {antes_inv!r} -> {partida.personaje.inventario!r}")
                if args.write:
                    repo.upsert(partida)
                    print("    persistido.")
            else:
                print(f"[ok]     {codigo} (ya en español)")
        except Exception as e:  # noqa: BLE001 — script one-off: seguir con el resto
            errores += 1
            print(f"[error]  {codigo}: {type(e).__name__}: {e}")

    print(
        f"\nResumen: {revisadas} revisadas, {cambiadas} "
        f"{'persistidas' if args.write else 'a cambiar'}, {errores} errores."
    )
    if not args.write and cambiadas:
        print("Dry-run: no se escribió nada. Volvé a correr con --write para aplicar.")
    return 1 if errores else 0


if __name__ == "__main__":
    raise SystemExit(main())
