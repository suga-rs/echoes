# partida-ownership

## Purpose

Attribution of partidas to a `user_id`. Authenticated players own the partidas
they create; anonymous and pre-existing (legacy) partidas belong to the built-in
`Creator` account (`user_id = "0"`). Listing is owner-scoped, while playing by
`codigo_partida` stays open to anyone holding the code.

## Requirements

### Requirement: Partidas have an owner

The system SHALL store a `user_id` on every partida identifying its owner. Partidas created by an authenticated user MUST be owned by that user; partidas created anonymously MUST be owned by the built-in `Creator` account (`user_id = "0"`).

#### Scenario: Authenticated user creates a partida

- **WHEN** an authenticated user starts a new partida
- **THEN** the persisted partida's `user_id` equals that user's id

#### Scenario: Anonymous play creates a partida

- **WHEN** a visitor with no valid token starts a new partida
- **THEN** the persisted partida's `user_id` equals `"0"` (the `Creator` account)

### Requirement: Built-in Creator account

The system SHALL provide a built-in account with `user_id = "0"` and username `Creator` that owns all legacy and anonymous partidas. This account MUST exist after migration and MUST NOT be creatable or impersonatable through normal registration.

#### Scenario: Creator account is seeded

- **WHEN** the migration runs
- **THEN** a user document with `user_id = "0"` and username `Creator` exists in the users container

### Requirement: Owner-scoped partida listing

The system SHALL scope partida listing to the caller. An authenticated request SHALL return only partidas owned by that user; an anonymous request SHALL return the `Creator` account's partidas, preserving the previously shared listing behavior.

#### Scenario: Authenticated listing

- **WHEN** an authenticated user requests the partida list
- **THEN** the system returns only partidas whose `user_id` equals that user's id

#### Scenario: Anonymous listing

- **WHEN** a request with no valid token asks for the partida list
- **THEN** the system returns partidas owned by the `Creator` account (`user_id = "0"`)

### Requirement: Legacy partida migration

The system SHALL backfill every pre-existing partida that lacks a `user_id` with `user_id = "0"` so that all historical partidas are owned by the `Creator` account.

#### Scenario: Backfill existing partidas

- **WHEN** the migration runs against partidas created before this change
- **THEN** each such partida is updated to `user_id = "0"` and remains otherwise unchanged

#### Scenario: Idempotent migration

- **WHEN** the migration runs a second time
- **THEN** partidas already owned are left unchanged and no duplicate `Creator` account is created

### Requirement: Resuming and playing partidas remains open by code

The system SHALL continue to allow resuming and advancing a partida by its `codigo_partida` regardless of authentication, preserving shareable-by-code behavior. Ownership affects listing and profile attribution, not the ability to play a known code.

#### Scenario: Resume by code without login

- **WHEN** any caller resumes or advances a partida using a valid `codigo_partida`
- **THEN** the system serves the partida regardless of whether the caller is authenticated or owns it

### Requirement: Owner-scoped partida deletion

The system SHALL allow an authenticated user to delete a partida they own via a delete operation keyed by `codigo_partida`. Deletion MUST be permitted only when the partida's `user_id` equals the caller's id and is not `"0"`. Requests from anonymous callers, requests for partidas owned by the `Creator` account (`user_id = "0"`), and requests for partidas owned by a different user MUST be rejected without deleting anything.

#### Scenario: Owner deletes their partida

- **WHEN** an authenticated user requests deletion of a partida whose `user_id` equals that user's id
- **THEN** the partida document is removed and the system responds with success

#### Scenario: Anonymous deletion is rejected

- **WHEN** a request with no valid token asks to delete any partida
- **THEN** the system rejects the request with an authentication error and the partida is left unchanged

#### Scenario: Creator-bucket partida cannot be deleted

- **WHEN** an authenticated user requests deletion of a partida owned by the `Creator` account (`user_id = "0"`)
- **THEN** the system rejects the request as forbidden and the partida is left unchanged

#### Scenario: Non-owner deletion is rejected

- **WHEN** an authenticated user requests deletion of a partida whose `user_id` belongs to a different user
- **THEN** the system rejects the request as forbidden and the partida is left unchanged

#### Scenario: Deleting an unknown code

- **WHEN** an authenticated user requests deletion of a `codigo_partida` that does not exist
- **THEN** the system responds with a not-found error

### Requirement: Partida image blobs are removed on deletion

When a partida is deleted, the system SHALL also remove its stored image blobs, including per-turn scene images and the character visual reference, so that deleting a partida leaves no orphaned image storage. Failure to remove a blob MUST NOT leave the partida document persisted (the document removal is the authoritative outcome of a successful delete).

#### Scenario: Blobs removed with the partida

- **WHEN** a partida that has generated images is deleted by its owner
- **THEN** the per-turn image blobs and the character visual reference blob for that partida are removed from storage

#### Scenario: Partida without images deletes cleanly

- **WHEN** a partida that never generated images is deleted by its owner
- **THEN** the partida document is removed and the operation succeeds with no blob errors
