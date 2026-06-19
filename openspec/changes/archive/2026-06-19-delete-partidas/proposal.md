## Why

Players have no way to remove partidas they no longer want; the list only grows.
Authenticated users own their partidas, so giving them a delete action is a safe,
expected piece of account hygiene. Anonymous/legacy partidas live in the shared
`Creator` bucket (`user_id = "0"`) and must stay protected from deletion.

## What Changes

- Add a `DELETE /api/partidas/{codigo}` endpoint that requires authentication and
  removes a partida the caller owns.
- Enforce ownership guards: deletion is allowed **only** when the partida's
  `user_id` matches the caller **and** is not `"0"`. Anonymous callers and the
  shared `Creator` bucket cannot delete.
- Clean up storage: deleting a partida also removes its image blobs (per-turn
  images and the character visual reference) so no orphaned blobs accumulate.
- Frontend: add a delete (trash) action with a confirmation step to the partidas
  list and the partidas sidebar, shown only to logged-in users. After deletion,
  refresh the list; if the active partida is deleted, reset local game state.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `partida-ownership`: add an owner-scoped deletion requirement (authenticated
  owner may delete; `Creator`/anonymous bucket is non-deletable) and require
  associated image blobs to be removed with the partida.

## Impact

- Backend:
  - `app/api/partidas.py` — new `DELETE` route behind `get_current_user`.
  - `app/services/partida_service.py` — `eliminar_partida(codigo, user_id)` with
    ownership guards, orchestrating blob then document deletion.
  - `app/repositories/partida_repo.py` — `delete(codigo)`.
  - `app/repositories/imagen_repo.py` — delete all blobs for a partida (turns +
    reference).
  - `app/core/exceptions.py` — may need a not-owner/forbidden error mapped to 403.
- Frontend:
  - `src/lib/api.ts` — `eliminarPartida(codigo)`.
  - `src/components/partidas-list.tsx`, `src/components/partida-sidebar.tsx` —
    trash button + confirm + query invalidation.
  - `src/store/partida-store.ts` / `src/app/page.tsx` — reset when the active
    partida is deleted.
- Tests: service ownership-guard tests; repo delete; frontend list/sidebar.
