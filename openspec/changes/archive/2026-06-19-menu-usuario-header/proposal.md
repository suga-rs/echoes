## Why

When a player is logged in, the header carries the username (linking to the
profile), a standalone log-out icon button, and a separate settings gear — three
controls competing for horizontal space alongside the inventory, code, home, and
"Nueva" buttons. The log-out icon in particular is always visible and rarely used.
Collapsing the per-user controls into a single dropdown opened from the username
declutters the header and groups profile / settings / log-out where users expect
them.

## What Changes

- Add a **user dropdown menu** opened by clicking the username/avatar in the
  header (logged-in state).
- The menu contains: **Ir al perfil**, **Ajustes** (opens the existing settings
  sheet), and **Cerrar sesión**.
- Remove the standalone log-out icon button from the header.
- Move the **settings gear into the user menu** for logged-in users. Logged-out /
  anonymous players keep the standalone gear so they retain access to theme/font.
- Add `@radix-ui/react-dropdown-menu` and a thin `ui/dropdown-menu.tsx` wrapper,
  consistent with the existing Radix-based primitives.

## Capabilities

### New Capabilities
- `user-menu`: a header dropdown, opened from the username, that consolidates the
  logged-in player's per-user actions (profile, settings, log out).

### Modified Capabilities
<!-- none -->

## Impact

- Frontend:
  - `src/components/ui/dropdown-menu.tsx` (new) — Radix dropdown-menu wrapper.
  - `src/components/header.tsx` — replace the username link + log-out icon with the
    dropdown trigger + menu; show the standalone gear only when logged out.
  - `package.json` — add `@radix-ui/react-dropdown-menu`.
- No backend changes.
