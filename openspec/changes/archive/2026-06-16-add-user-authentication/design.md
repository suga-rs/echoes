## Context

Echoes is a FastAPI + Next.js app. The backend is layered (`api → services → repositories`) and persists all game state in a single Cosmos DB account (container `partidas`, partition key = `codigo_partida`), with images in Azure Blob Storage. There is currently no concept of a user: partidas are anonymous and addressed only by their shareable code. The frontend (Zustand + React Query) persists only `codigoPartida` to `localStorage` and re-hydrates from the backend.

This change introduces optional username/password accounts, attributes partidas to a `user_id`, and adds a profile page with an avatar. Per product decisions: **login is optional** (anonymous play remains), and the session is carried as a **JWT in `localStorage`** sent via `Authorization: Bearer`.

## Goals / Non-Goals

**Goals:**
- Username + password registration and login, passwords hashed (bcrypt).
- Stateless JWT auth that coexists with anonymous access.
- Every partida owned by a `user_id`; legacy + anonymous partidas owned by a built-in `Creator` account (`user_id = "0"`).
- Owner-scoped partida listing and a profile page (username, creation date, owned partidas, avatar).
- Avatar upload to Blob Storage.
- Reuse the existing layered architecture and Azure clients.

**Non-Goals:**
- Email, email verification, password reset, OAuth/social login.
- Roles/permissions beyond owner vs. anonymous.
- Transferring or claiming existing anonymous partidas into a user account.
- Token refresh/rotation, logout token blacklist (logout is client-side token discard).
- Locking play by code behind auth — partidas remain playable by anyone holding the code.

## Decisions

### Storage: new Cosmos container `usuarios`
A dedicated container `usuarios` with partition key `/id` (the `user_id`). User document:
```
{ "id": "<uuid|0>", "username": "<str>", "username_lower": "<str>",
  "password_hash": "<bcrypt>", "creada_en": "<iso8601>", "avatar_url": "<str|null>" }
```
Uniqueness of username is enforced via a `username_lower` lookup query before insert (Cosmos has no unique secondary index across partitions without a unique-key policy; we set a **unique key policy on `/username_lower`** at container creation as the hard guarantee, with a pre-check for a friendly 409).
- *Alternative considered:* reuse the `partidas` container with a `type` discriminator. Rejected — mixing entity types complicates queries and the existing `list_all` query.

### Password hashing: bcrypt via `passlib`
`passlib[bcrypt]` (`CryptContext`) for hashing/verification. Standard, well-vetted, tunable cost.
- *Alternative:* raw `bcrypt`/`argon2`. `passlib` chosen for a clean verify/needs-update API and to match common FastAPI guides.

### Tokens: JWT via `pyjwt`, HS256
Login/register return `{ access_token, token_type: "bearer", user }`. JWT claims: `sub = user_id`, `exp`. Signed HS256 with `JWT_SECRET`. Verified in a FastAPI dependency.
- Two dependencies in `app/api/dependencies.py`:
  - `get_current_user` → requires a valid token, else 401 (protected endpoints: profile, avatar).
  - `get_optional_user` → returns the user or `None` (optionally-authenticated endpoints: list partidas, start partida).
- *Alternative:* server-side sessions / httpOnly cookies. Rejected per product decision (matches existing `localStorage` pattern; avoids CSRF/CORS-credentials complexity).

### Ownership model
Add `user_id: str` to the partida document (on `MetadataPartida` to keep the top-level shape stable, or as a top-level field — see Open Questions). `PartidaService.crear_partida` accepts an optional `owner_id`, defaulting to `"0"` when anonymous. The route resolves `owner_id` from `get_optional_user`.
- Listing: `PartidaRepository.list_all` gains a `user_id` filter (`WHERE c.metadata.user_id = @uid`). The route passes the caller's id, or `"0"` when anonymous.
- Playing by code (`/turn`, `/resume`, `/state`, image, feedback) is unchanged and stays open by code.

### Avatars in Blob Storage
Reuse the existing storage account via `ImagenRepository` (or a sibling method) into a separate container `avatares`. Blob name `avatar/{user_id}.{ext}`, `overwrite=True` so a new upload replaces the old. Validate content-type (png/jpeg/webp) and a max size before upload. Endpoint accepts `multipart/form-data`.
- *Alternative:* base64 in the user document. Rejected — Cosmos item size limits and cost.

### Migration: standalone idempotent script
A script `backend/scripts/migrate_user_ids.py` (run once) that:
1. Upserts the `Creator` user (`id="0"`, `username="Creator"`, random unusable password hash, `creada_en=now`) if absent.
2. Queries partidas missing `metadata.user_id` and upserts each with `user_id="0"`.
Idempotent: re-runs skip already-owned partidas and don't duplicate `Creator`.
- *Alternative:* lazy backfill on read. Rejected — leaves data inconsistent and complicates listing queries.

### Frontend
- `src/store/auth-store.ts`: Zustand store persisting `{ token, user }` to `localStorage` (key `aventuras-auth`).
- `src/lib/api.ts`: add `register`, `login`, `getPerfil`, `uploadAvatar`; the shared `request` helper injects `Authorization: Bearer` when a token is present.
- `src/components/auth-modal.tsx`: tabbed login/register dialog (reuses `ui/dialog`, `ui/input`).
- `header.tsx`: when logged out, an "Iniciar sesión" button opening the modal; when logged in, an avatar/username control linking to the profile and offering logout.
- Profile page: a new route `src/app/perfil/page.tsx` showing username, creation date, avatar with upload control, and the user's partidas list (reusing `partidas-list.tsx`).
- React Query keys for partida lists become user-scoped so they refetch on login/logout.

## Risks / Trade-offs

- **JWT in `localStorage` is XSS-exposed** → Mitigation: short-ish expiry (`JWT_EXPIRE_MINUTES`, default e.g. 1 week), strict input handling; documented trade-off accepted for scope. No secrets beyond the token are stored.
- **Cosmos cross-partition uniqueness** → Mitigation: container-level unique-key policy on `/username_lower` plus pre-check. The policy must be set at creation (cannot be added later) — document container provisioning.
- **`get_settings()` and service deps are `@lru_cache`'d singletons** → new repos/services must be wired consistently; the auth dependency should not break the cached `PartidaService`. Mitigation: add `UsuarioRepository`/`AuthService` as their own cached deps.
- **Optional-auth ambiguity** → an expired/garbage token on an optional endpoint: we treat invalid tokens as 401 even on optional endpoints (only a *missing* token means anonymous), so clients clear bad tokens rather than silently degrading. Documented in the `user-auth` spec.
- **Adding `user_id` to existing model** → Cosmos is schemaless; old docs read back without the field. Pydantic must default `user_id` (and migration backfills) to avoid validation errors on legacy reads.
- **Avatar uploads** add a `python-multipart` dependency and file-validation surface → enforce type + size limits server-side.

## Migration Plan

1. Provision the `usuarios` Cosmos container (partition key `/id`, unique key policy on `/username_lower`) and the `avatares` Blob container.
2. Set new env vars (`JWT_SECRET`, `JWT_EXPIRE_MINUTES`, `COSMOS_USUARIOS_CONTAINER`, `STORAGE_AVATARES_CONTAINER`) in `.env` / deployment config and `.env.example`.
3. Deploy backend (new endpoints are additive; existing endpoints stay backward compatible for anonymous callers).
4. Run `migrate_user_ids.py` once to seed `Creator` and backfill `user_id="0"`.
5. Deploy frontend.
6. **Rollback:** the migration only adds a field and one user doc; reverting code leaves data harmless (extra `user_id` ignored by old code). Drop the `usuarios`/`avatares` containers if fully reverting.

## Open Questions

- Place `user_id` on `MetadataPartida` (keeps `list_all` query path `c.metadata.user_id`) vs. a top-level partida field? Leaning `metadata.user_id` for query consistency — confirm during implementation.
- JWT expiry default value (proposed 1 week) — confirm acceptable for the assignment.
- Should anonymous partidas be claimable post-login later? Out of scope now; note as future work.
