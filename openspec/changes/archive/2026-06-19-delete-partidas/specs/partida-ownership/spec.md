## ADDED Requirements

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
