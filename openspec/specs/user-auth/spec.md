# user-auth

## Purpose

Lightweight username/password accounts for Echoes: registration, login, and
token-based authentication. Login is optional — anonymous play continues to
work, and authentication carries via a signed JWT in the `Authorization: Bearer`
header. Email and email verification are explicitly out of scope.

## Requirements

### Requirement: Account registration

The system SHALL allow a visitor to create an account with a unique username and a password. The username MUST be unique (case-insensitive); the password MUST be stored only as a salted hash, never in plaintext. Email and email verification are explicitly NOT required.

#### Scenario: Successful registration

- **WHEN** a visitor submits a username that is not already taken and a password meeting the minimum length
- **THEN** the system creates a new user document in Cosmos DB with a generated `user_id`, the username, a bcrypt password hash, and a creation timestamp
- **AND** returns a signed JWT and the public user profile (without the password hash)

#### Scenario: Duplicate username

- **WHEN** a visitor submits a username that already exists (case-insensitive match)
- **THEN** the system rejects the request with a 409 conflict error and does not create a user

#### Scenario: Invalid credentials format

- **WHEN** a visitor submits a username or password that does not meet the length constraints (username 3–32 chars, password ≥ 8 chars)
- **THEN** the system rejects the request with a 422 validation error and does not create a user

#### Scenario: Reserved Creator account cannot be registered

- **WHEN** a visitor attempts to register the username `Creator` or a `user_id` of `0`
- **THEN** the system rejects the request because the `Creator` account is reserved

### Requirement: Login and token issuance

The system SHALL authenticate a user by username and password and issue a signed JWT on success. The JWT MUST encode the `user_id` and an expiry, and MUST be signed with the configured secret.

#### Scenario: Successful login

- **WHEN** a user submits a correct username and password
- **THEN** the system verifies the password against the stored hash and returns a signed JWT plus the public user profile

#### Scenario: Wrong password

- **WHEN** a user submits a correct username but an incorrect password
- **THEN** the system rejects the request with a 401 error and does not reveal whether the username exists

#### Scenario: Unknown username

- **WHEN** a user submits a username that does not exist
- **THEN** the system rejects the request with a 401 error using the same message as a wrong password

### Requirement: Current-user resolution from token

The system SHALL resolve the authenticated user from an `Authorization: Bearer <token>` header on protected and optionally-authenticated endpoints. Login is optional: endpoints that support anonymous access MUST treat a missing token as the anonymous (`Creator`) context rather than an error.

#### Scenario: Valid token resolves to user

- **WHEN** a request carries a valid, unexpired bearer token
- **THEN** the system resolves the request to the corresponding `user_id`

#### Scenario: Missing token on an optionally-authenticated endpoint

- **WHEN** a request to an optionally-authenticated endpoint carries no bearer token
- **THEN** the system treats the request as anonymous (the `Creator` context) and proceeds

#### Scenario: Invalid or expired token

- **WHEN** a request carries a malformed, tampered, or expired bearer token
- **THEN** the system rejects the request with a 401 error

#### Scenario: Missing token on a protected endpoint

- **WHEN** a request to a protected endpoint (e.g. profile, avatar upload) carries no valid token
- **THEN** the system rejects the request with a 401 error
