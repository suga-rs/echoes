## Why

Today every adventure is anonymous and keyed only by a shareable `codigo_partida`; there is no notion of a player account, so users cannot see "my games" in one place, and partidas cannot be attributed to anyone. Adding a lightweight username/password account lets players own their adventures, view a personal profile, and keep their history across devices — without the friction of email verification flows we don't need.

## What Changes

- Add username + password registration and login. Passwords are stored hashed (never plaintext) in the existing Cosmos DB instance.
- Issue a signed JWT on login; the frontend stores it in `localStorage` and sends it as `Authorization: Bearer <token>`. Login is **optional** — anonymous play continues to work.
- Associate every partida with a `user_id`. Logged-in players own the partidas they create; anonymous play and all pre-existing partidas belong to a built-in `Creator` account (`user_id = "0"`).
- Scope partida listing to the caller: authenticated requests list that user's partidas; anonymous requests list the `Creator` bucket (preserving today's shared behavior).
- Add a profile avatar uploaded to Azure Blob Storage.
- Frontend: a login/register modal, a login/account button in the header, and a user profile page showing username, account creation date, the user's list of partidas, and the avatar.
- One-time data migration: backfill all existing partidas with `user_id = "0"` and seed the `Creator` user document.

## Capabilities

### New Capabilities
- `user-auth`: account registration, password hashing, login, and JWT issuance/verification; resolving the current user (or anonymous) from a request.
- `user-profile`: profile data retrieval (username, creation date, owned partidas) and avatar upload/storage in Blob Storage.
- `partida-ownership`: attaching a `user_id` to partidas, owner-scoped listing, the built-in `Creator` account, and migration of legacy partidas.

### Modified Capabilities
<!-- No existing specs in openspec/specs/; all behavior is introduced as new capabilities above. -->

## Impact

- **Backend code:**
  - New: `app/repositories/usuario_repo.py`, `app/services/auth_service.py`, `app/api/auth.py`, `app/api/usuarios.py`, `app/core/security.py` (hashing + JWT), auth dependency in `app/api/dependencies.py`.
  - Modified: `app/models/domain.py` (Usuario model, auth DTOs, `user_id` on partidas), `app/repositories/partida_repo.py` (filter by `user_id`), `app/repositories/imagen_repo.py` (avatar upload), `app/services/partida_service.py` (set owner on create, scope listing), `app/core/config.py` (JWT + new container settings), `app/main.py` (register routers).
  - New Cosmos container `usuarios`; new Blob container/path for avatars.
  - Migration script to backfill `user_id` and seed `Creator`.
- **New dependencies:** `passlib[bcrypt]` (or `bcrypt`) for hashing, `pyjwt` for tokens.
- **API:** new endpoints under `/api/auth` and `/api/usuarios`; existing `GET /api/partidas` and `/start` become user-aware (backward compatible for anonymous callers).
- **Frontend:** new auth store, auth API functions, login/register modal, header account control, `/perfil` profile page; partida API calls send the bearer token when present.
- **Env vars:** `JWT_SECRET`, `JWT_EXPIRE_MINUTES`, `COSMOS_USUARIOS_CONTAINER`, `STORAGE_AVATARES_CONTAINER`.
