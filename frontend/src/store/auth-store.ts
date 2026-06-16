/**
 * Estado global de autenticación.
 *
 * Persiste el token JWT y el usuario público en localStorage. El token se
 * adjunta a las peticiones al backend (ver `lib/api.ts`). Login opcional: si no
 * hay token, la app funciona en modo anónimo.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { UsuarioPublico } from "@/lib/types";

interface AuthState {
  token: string | null;
  user: UsuarioPublico | null;

  login: (token: string, user: UsuarioPublico) => void;
  logout: () => void;
  setUser: (user: UsuarioPublico) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,

      login: (token, user) => set({ token, user }),
      logout: () => set({ token: null, user: null }),
      setUser: (user) => set({ user }),
    }),
    {
      name: "aventuras-auth",
    },
  ),
);

/** Lee el token actual fuera de React (para el cliente HTTP). */
export function getAuthToken(): string | null {
  return useAuthStore.getState().token;
}
