## 1. Backend — repositories

- [x] 1.1 Add `delete(codigo_partida)` to `PartidaRepository` using `delete_item(item=codigo, partition_key=codigo)`, raising `PartidaNoEncontradaError` on `CosmosResourceNotFoundError`.
- [x] 1.2 Add a method to `ImagenRepository` that deletes all blobs for a partida (per-turn images + character reference) by its blob prefix; log and continue on individual blob failures.

## 2. Backend — service & errors

- [x] 2.1 Add `AccesoDenegadoError` (code `acceso_denegado`, HTTP 403) to `app/core/exceptions.py` and map it in `app/main.py`. (Mapping is automatic via the generic `AppError` handler in `main.py`.)
- [x] 2.2 Write failing service tests: owner deletes (success + blob cleanup invoked), `user_id == "0"` rejected (403), non-owner rejected (403), unknown code (404).
- [x] 2.3 Implement `PartidaService.eliminar_partida(codigo, user_id)`: load partida, guard `metadata.user_id != "0"`, guard `metadata.user_id == user_id`, delete blobs (best-effort), then delete document. Make tests pass.

## 3. Backend — API

- [x] 3.1 Add `DELETE /api/partidas/{codigo}` in `app/api/partidas.py` behind `get_current_user`; call `service.eliminar_partida(codigo, user_id)`; return 204/success.
- [x] 3.2 Add/verify route test: unauthenticated request → 401; authenticated owner → success.

## 4. Frontend — API & state

- [x] 4.1 Add `eliminarPartida(codigo)` to `src/lib/api.ts` (DELETE, auth headers).
- [x] 4.2 Add a shared delete mutation hook: calls `api.eliminarPartida`, invalidates `["partidas"]`, and resets the store (`resetear()`) when the deleted code is the active `codigoPartida`.

## 5. Frontend — UI

- [x] 5.1 Add a trash icon-button with a confirmation step to each row in `src/components/partidas-list.tsx`, rendered only when `useAuthStore().user` is truthy.
- [x] 5.2 Add the same delete affordance to `src/components/partida-sidebar.tsx` (compact inline confirm), reusing the shared hook.
- [x] 5.3 Verify `src/app/page.tsx` clears the open game when the active partida is deleted. (Hook calls `resetear()`; `codigo` becomes null → welcome screen shows and the sidebar unmounts.)

## 6. Tests & verification

- [x] 6.1 Frontend tests: delete button hidden when logged out, visible when logged in; confirm + mutation wiring; active-partida reset.
- [x] 6.2 Run `pytest`, `ruff check .`, `pnpm lint`, `pnpm typecheck` and fix issues.
