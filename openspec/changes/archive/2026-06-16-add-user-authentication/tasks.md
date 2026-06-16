## 1. Backend setup & config

- [x] 1.1 Add dependencies to `backend/pyproject.toml`: `passlib[bcrypt]`, `pyjwt`, `python-multipart`; reinstall with `pip install -e .[dev]`.
- [x] 1.2 Add settings to `app/core/config.py`: `jwt_secret`, `jwt_expire_minutes` (default 10080), `jwt_algorithm` (default `HS256`), `cosmos_usuarios_container` (default `usuarios`), `storage_avatares_container` (default `avatares`).
- [x] 1.3 Update `backend/.env.example` and `frontend/.env.local.example` with the new vars; document them in `CLAUDE.md` env table.

## 2. Domain models & security utils

- [x] 2.1 In `app/models/domain.py` add `Usuario` (id, username, username_lower, password_hash, creada_en, avatar_url) and public `UsuarioPublico` (no hash); add auth DTOs `RegisterRequest`, `LoginRequest`, `AuthResponse`, `PerfilResponse`.
- [x] 2.2 Add `user_id: str` to `MetadataPartida` with default `"0"` so legacy docs deserialize; thread it through `PartidaResumen` if needed.
- [x] 2.3 Create `app/core/security.py`: `hash_password`, `verify_password` (passlib bcrypt), `create_access_token`, `decode_access_token` (pyjwt HS256).

## 3. Repositories

- [x] 3.1 Create `app/repositories/usuario_repo.py`: build `usuarios` container client; `get(user_id)`, `get_by_username(username_lower)`, `create(usuario)` with duplicate handling, `upsert(usuario)`.
- [x] 3.2 Add avatar upload to `app/repositories/imagen_repo.py` (or sibling): `subir_avatar(user_id, contenido, ext) -> url` into the `avatares` container with `overwrite=True`.
- [x] 3.3 Modify `app/repositories/partida_repo.py`: add optional `user_id` filter to `list_all` (default returns Creator/`"0"` set).

## 4. Auth service & dependencies

- [x] 4.1 Create `app/services/auth_service.py`: `register(username, password)` (reject reserved `Creator`/`0`, enforce uniqueness, hash, persist, issue token), `login(username, password)` (verify, issue token), `get_perfil(user_id)` (compose profile + owned partidas), `set_avatar(user_id, file)`.
- [x] 4.2 In `app/api/dependencies.py` add cached `get_usuario_repo`, `get_auth_service`; add `get_current_user` (401 if no/invalid token) and `get_optional_user` (None on missing token, 401 on invalid token) using `decode_access_token`.

## 5. API routes

- [x] 5.1 Create `app/api/auth.py` (prefix `/api/auth`): `POST /register`, `POST /login` returning `AuthResponse`.
- [x] 5.2 Create `app/api/usuarios.py` (prefix `/api/usuarios`): `GET /me` (protected) returning `PerfilResponse`; `POST /me/avatar` (protected, multipart) returning new avatar URL with type/size validation.
- [x] 5.3 Modify `app/api/partidas.py`: `GET ""` and `POST /start` use `get_optional_user`; pass `owner_id` (user id or `"0"`) into the service.
- [x] 5.4 Modify `app/services/partida_service.py`: `crear_partida` accepts `owner_id` and stamps `metadata.user_id`; `listar_partidas` accepts `user_id` and filters.
- [x] 5.5 Register the new routers in `app/main.py`.

## 6. Migration

- [x] 6.1 Create `backend/scripts/migrate_user_ids.py`: idempotently seed the `Creator` user (`id="0"`) and backfill all partidas missing `metadata.user_id` to `"0"`.
- [x] 6.2 Document how to provision the `usuarios` container (partition key `/id`, unique key policy on `/username_lower`) and `avatares` Blob container, and how to run the migration.

## 7. Backend tests

- [x] 7.1 Tests for `security.py`: hash/verify round-trip, token encode/decode, expired/tampered token rejection.
- [x] 7.2 Tests for `auth_service`: successful register, duplicate username (409), reserved `Creator`, wrong password / unknown username (401, same message).
- [x] 7.3 Tests for ownership: authenticated start stamps user id; anonymous start stamps `"0"`; listing scoped by caller; resume-by-code works unauthenticated.
- [x] 7.4 Tests for profile/avatar endpoints: protected without token (401), profile excludes hash, avatar rejects bad type/size.
- [x] 7.5 Tests for migration idempotency (backfill once, re-run no-op).

## 8. Frontend

- [x] 8.1 Regenerate API types (`pnpm gen:types`) and/or extend `src/lib/types.ts` with `UsuarioPublico`, `PerfilResponse`, auth requests/responses.
- [x] 8.2 Create `src/store/auth-store.ts`: Zustand store persisting `{ token, user }` to `localStorage`; `login`, `logout`, `setUser` actions.
- [x] 8.3 Extend `src/lib/api.ts`: shared `request` injects `Authorization: Bearer` when a token exists; add `register`, `login`, `getPerfil`, `uploadAvatar`.
- [x] 8.4 Create `src/components/auth-modal.tsx`: tabbed login/register dialog with validation and error display.
- [x] 8.5 Update `src/components/header.tsx`: logged-out shows "Iniciar sesión" button opening the modal; logged-in shows avatar/username with link to profile + logout.
- [x] 8.6 Create `src/app/perfil/page.tsx`: profile page with username, creation date, avatar (with upload control), and the user's partidas list (reuse `partidas-list.tsx`).
- [x] 8.7 Make partida-list React Query keys user-scoped so they refetch on login/logout.

## 9. Frontend tests & verification

- [x] 9.1 Add/extend tests for the auth store and `api.ts` token injection.
- [x] 9.2 Run `ruff check .`, `ruff format .`, `pytest` (backend) and `pnpm lint`, `pnpm typecheck`, `pnpm build` (frontend); fix failures.
- [x] 9.3 Manual smoke: register → login → start partida (owned) → view profile with avatar upload → logout → anonymous start lands in Creator bucket.
