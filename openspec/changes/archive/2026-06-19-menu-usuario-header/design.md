## Context

The header (`src/components/header.tsx`) renders, for a logged-in user, a `Button`
wrapping a `next/link` to `/perfil` (avatar + username) plus a separate log-out
icon `Button`, and — unconditionally — a settings gear `Button` that opens the
`SettingsSheet`. Auth state comes from `useAuthStore` (`user`, `logout`); log-out
also invalidates the `partidas` query. The project uses Radix primitives
(`dialog`, `select`, `sheet`, `label`) wrapped in `src/components/ui/*`. There is
no dropdown/menu primitive yet.

## Goals / Non-Goals

**Goals:**
- One trigger (username/avatar) opens a menu with profile, settings, and log out.
- Drop the standalone log-out icon from the header.
- Keep settings reachable for both logged-in (in the menu) and logged-out (gear).

**Non-Goals:**
- Changing what log-out does, the profile route, or the settings sheet itself.
- A general app-wide menu/command system — only the per-user header menu.
- Reworking the other header controls (inventory, code, home, "Nueva").

## Decisions

### Radix dropdown-menu + a `ui/dropdown-menu.tsx` wrapper

Add `@radix-ui/react-dropdown-menu` and a thin wrapper mirroring the existing
`ui/` primitives. Rationale: consistent with the project's Radix usage and gets
keyboard navigation, click-outside, focus management, and escape-to-close for free
rather than hand-rolling them. Trade-off: one new dependency — accepted as the
idiomatic choice here.

### Settings: in the menu when logged in, standalone gear when logged out

The gear is currently always visible. Moving it into the user menu would strand
anonymous players (the app supports anonymous play via locally-persisted
`codigoPartida`), so the standalone gear is rendered only in the logged-out branch;
logged-in players reach settings via the menu's "Ajustes" entry. The
`SettingsSheet` and its `showSettings` state are unchanged — only the trigger
moves.

### Trigger shape

The username/avatar becomes the menu trigger (with a caret affordance) instead of
a link. "Ir al perfil" inside the menu carries the navigation that the trigger
used to perform. Net header change for logged-in users: two controls (profile
link + log-out) and the gear collapse into a single trigger.

## Risks / Trade-offs

- [New dependency] → Accepted; matches existing Radix-based primitives.
- [Profile no longer one click] → Navigation moves into the menu; acceptable for
  the decluttering benefit, and matches the requested behavior.
- [Settings discoverability when logged in] → Lives under the user menu; logged-out
  users keep the visible gear so anonymous access is unaffected.

## Open Questions

- Whether to also fold theme/other future header actions into this menu later —
  out of scope for now.
