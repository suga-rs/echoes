## 1. Dropdown primitive

- [x] 1.1 Add `@radix-ui/react-dropdown-menu` to `frontend/package.json` and install.
- [x] 1.2 Create `src/components/ui/dropdown-menu.tsx` wrapping the Radix parts (Root, Trigger, Content, Item, Separator) with the project's Tailwind styling, mirroring the existing `ui/` primitives.

## 2. Header integration

- [x] 2.1 Write a failing component test for the header: logged-in user shows a menu trigger (username), opening it reveals "Ir al perfil", "Ajustes", and "Cerrar sesión", and there is no standalone log-out icon.
- [x] 2.2 Replace the username link + standalone log-out button in `src/components/header.tsx` with the dropdown trigger (username/avatar + caret) and menu items.
- [x] 2.3 Wire menu items: "Ir al perfil" navigates to `/perfil`, "Ajustes" opens the settings sheet (`setShowSettings(true)`), "Cerrar sesión" runs the existing `cerrarSesion`.
- [x] 2.4 Render the standalone settings gear only when logged out; for logged-in users settings is reached via the menu.

## 3. Tests & verification

- [x] 3.1 Make the header test pass; add a test (or assertion) that the gear is present when logged out and absent (as a standalone button) when logged in.
- [x] 3.2 Run `pnpm lint`, `pnpm typecheck`, and frontend tests; fix issues.
- [x] 3.3 Manually verify: logged-in menu (profile nav, settings opens, log-out works) and logged-out header still exposes settings, in light and dark theme.
