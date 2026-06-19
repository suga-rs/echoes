## ADDED Requirements

### Requirement: User dropdown menu in the header

When a player is logged in, the header SHALL present the player's username/avatar
as the trigger for a dropdown menu, instead of a direct profile link plus a
standalone log-out button. The menu SHALL contain entries to go to the profile,
open the settings panel, and log out.

#### Scenario: Open the user menu

- **WHEN** a logged-in player activates the username/avatar control in the header
- **THEN** a dropdown menu opens below it with "Ir al perfil", "Ajustes", and
  "Cerrar sesión" entries

#### Scenario: Go to profile from the menu

- **WHEN** the player selects "Ir al perfil" from the menu
- **THEN** the app navigates to the profile page

#### Scenario: Log out from the menu

- **WHEN** the player selects "Cerrar sesión" from the menu
- **THEN** the session is ended (as the standalone log-out button did previously)

#### Scenario: No standalone log-out button

- **WHEN** a player is logged in
- **THEN** the header shows no separate log-out icon button outside the menu

### Requirement: Settings access preserved in both auth states

The settings panel SHALL remain reachable whether or not the player is logged in.
For logged-in players the settings entry SHALL live inside the user menu; for
logged-out players a settings control SHALL remain directly available in the
header.

#### Scenario: Settings inside the menu when logged in

- **WHEN** a logged-in player opens the user menu and selects "Ajustes"
- **THEN** the settings panel opens

#### Scenario: Settings still reachable when logged out

- **WHEN** a logged-out player views the header
- **THEN** a settings control is directly available (not hidden behind a user menu)
