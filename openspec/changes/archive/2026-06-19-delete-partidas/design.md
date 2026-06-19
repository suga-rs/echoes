## Context

Partidas are persisted in Cosmos DB (`PartidaRepository`, partition key =
`codigo_partida` = document `id`). Images live in Azure Blob Storage via
`ImagenRepository`: per-turn scene images plus a single character visual
reference (memoized on `personaje.referencia_visual_url`). Ownership is tracked
by `metadata.user_id`, where `"0"` is the shared `Creator`/anonymous bucket and
authenticated users carry their real id. Listing is already owner-scoped
(`get_optional_user`). There is currently no delete path at any layer.

The shared `"0"` bucket is the key constraint: many anonymous sessions and all
legacy partidas resolve to it, so deletion there would let any one caller remove
games visible to everyone. Deletion must therefore be restricted to authenticated
owners of non-`"0"` partidas.

## Goals / Non-Goals

**Goals:**
- Let an authenticated user delete a partida they own.
- Refuse deletion for anonymous callers, the `"0"` bucket, and non-owners.
- Remove the partida's image blobs so no orphaned storage remains.
- Keep the frontend list/sidebar in sync after deletion and reset local state
  when the active partida is deleted.

**Non-Goals:**
- Soft delete / trash / undo. Deletion is permanent.
- Bulk deletion or deleting by selecting multiple partidas.
- Changing how partidas are played or resumed by code.
- Reclaiming the character reference blob when shared across partidas — each
  partida owns its own blob prefix, so no cross-partida sharing exists.

## Decisions

### Authorization: `DELETE` requires a valid token (`get_current_user`)

Unlike listing (`get_optional_user`), delete uses `get_current_user`, so a
missing/invalid token is a 401 before any ownership logic runs. The service then
loads the partida and applies two guards:
- `metadata.user_id != "0"` → else 403 (shared bucket is non-deletable).
- `metadata.user_id == caller_id` → else 403 (not your partida).

Order: a missing partida raises `PartidaNoEncontradaError` (404). We check
existence first (load), then ownership, to give an honest 404 vs 403. Returning
404 for "not yours" was considered to avoid leaking existence, but the codes are
shareable-by-design here, so a clear 403 is fine and simpler.

A new `AppError` subclass (e.g. `AccesoDenegadoError`, code `acceso_denegado`,
HTTP 403) is added and mapped in `main.py` alongside the existing hierarchy.

### Blob cleanup: delete blobs by prefix, then the document

`ImagenRepository` gets a method to delete every blob under the partida's prefix
(turn images + reference). The service deletes blobs first, then the Cosmos
document. Rationale: the document is the index of record; once it's gone the
partida is effectively deleted from the user's perspective. If a blob delete
fails we log and continue to the document delete so a storage hiccup can't strand
the document forever. The spec makes document removal the authoritative outcome.

Alternative considered: delete document first, then blobs. Rejected because a
crash between steps would orphan blobs with no document pointing at them, which is
exactly the cost we're trying to avoid.

### Frontend: shared delete affordance, gated on auth

A trash icon-button appears on each partida row in both `partidas-list.tsx` and
`partida-sidebar.tsx`, rendered only when `useAuthStore().user` is truthy. Since
the list endpoint already returns only the caller's own (non-`"0"`) partidas when
authenticated, every visible row for a logged-in user is deletable — no per-row
ownership check is needed client-side.

A confirmation step guards the destructive action (a small inline confirm or a
dialog). On success the `["partidas"]` query is invalidated. If the deleted code
equals the active `codigoPartida`, call `resetear()` so the open game clears.

A `useMutation` wraps `api.eliminarPartida(codigo)`; both components can share a
small hook to avoid duplicating invalidation + active-reset logic.

## Risks / Trade-offs

- [Blob delete is best-effort] → A failed blob delete still removes the document,
  potentially leaving an orphaned blob. Mitigation: log failures; acceptable
  because the alternative (stranded document) is worse, and blobs are cheap.
- [Permanent deletion, no undo] → Mitigation: explicit confirm step in the UI.
- [Two list surfaces drift] → list and sidebar both need the action. Mitigation:
  share a mutation hook so behavior stays identical.
- [Legacy partidas a user "adopted" anonymously stay in `"0"`] → those won't show
  in their authenticated list and can't be deleted. Accepted; consistent with the
  existing ownership model and out of scope.

## Open Questions

- Confirmation UX: inline "click again to confirm" vs. a dialog. Leaning inline
  for the sidebar (compact) and either for the list; final call at implementation.
