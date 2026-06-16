import { beforeEach, describe, expect, it } from "vitest";
import type { UsuarioPublico } from "@/lib/types";
import { getAuthToken, useAuthStore } from "@/store/auth-store";

const user: UsuarioPublico = {
  id: "u1",
  username: "Lyra",
  creada_en: "2026-06-16T12:00:00Z",
  avatar_url: null,
};

beforeEach(() => {
  useAuthStore.getState().logout();
});

describe("auth-store", () => {
  it("login setea token y usuario", () => {
    useAuthStore.getState().login("tok-123", user);
    expect(useAuthStore.getState().token).toBe("tok-123");
    expect(useAuthStore.getState().user?.username).toBe("Lyra");
    expect(getAuthToken()).toBe("tok-123");
  });

  it("logout limpia token y usuario", () => {
    useAuthStore.getState().login("tok-123", user);
    useAuthStore.getState().logout();
    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().user).toBeNull();
    expect(getAuthToken()).toBeNull();
  });

  it("setUser actualiza el usuario sin tocar el token", () => {
    useAuthStore.getState().login("tok-123", user);
    useAuthStore.getState().setUser({ ...user, avatar_url: "https://x/a.png" });
    expect(useAuthStore.getState().token).toBe("tok-123");
    expect(useAuthStore.getState().user?.avatar_url).toBe("https://x/a.png");
  });
});
