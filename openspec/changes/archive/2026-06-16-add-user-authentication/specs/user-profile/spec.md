## ADDED Requirements

### Requirement: Retrieve own profile

The system SHALL return the authenticated user's profile, consisting of username, account creation date, avatar URL (if any), and the list of partidas owned by that user.

#### Scenario: Authenticated profile fetch

- **WHEN** an authenticated user requests their profile
- **THEN** the system returns their username, creation date, avatar URL, and a list of their partidas (each with code, character name, genre, current turn, state, and timestamps)

#### Scenario: Unauthenticated profile fetch

- **WHEN** a request for the profile carries no valid token
- **THEN** the system rejects it with a 401 error

#### Scenario: Profile excludes secrets

- **WHEN** any profile is returned
- **THEN** the response MUST NOT include the password hash or any internal authentication fields

### Requirement: Avatar upload

The system SHALL allow an authenticated user to upload a profile avatar image, store it in Azure Blob Storage, and persist the resulting URL on the user document. A newly uploaded avatar MUST replace the reference to any previous one.

#### Scenario: Successful avatar upload

- **WHEN** an authenticated user uploads a valid image file (png/jpeg/webp) within the size limit
- **THEN** the system stores the image in the avatars Blob container keyed by `user_id`, updates the user's `avatar_url`, and returns the new URL

#### Scenario: Rejected file type

- **WHEN** an authenticated user uploads a file whose type is not an allowed image type or exceeds the size limit
- **THEN** the system rejects the request with a 422 error and does not modify the stored avatar

#### Scenario: Unauthenticated upload

- **WHEN** an avatar upload request carries no valid token
- **THEN** the system rejects it with a 401 error

### Requirement: Default avatar fallback

The system SHALL represent users without an uploaded avatar with a null `avatar_url`, allowing the frontend to render a default placeholder.

#### Scenario: User without avatar

- **WHEN** a user who has never uploaded an avatar is returned in any profile response
- **THEN** the `avatar_url` field is `null`
