import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/lib/api";
import { EliminarPartidaButton } from "@/components/eliminar-partida-button";
import type { UsuarioPublico } from "@/lib/types";
import { useAuthStore } from "@/store/auth-store";
import { usePartidaStore } from "@/store/partida-store";

vi.mock("@/lib/api", () => ({
  api: { eliminarPartida: vi.fn().mockResolvedValue(undefined) },
}));

const USUARIO: UsuarioPublico = {
  id: "u1",
  username: "alguien",
  creada_en: "2026-01-01T00:00:00Z",
  avatar_url: null,
};

function renderConProviders(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({ token: null, user: null });
  usePartidaStore.getState().resetear();
});

describe("EliminarPartidaButton", () => {
  it("no se muestra para usuarios anónimos", () => {
    renderConProviders(<EliminarPartidaButton codigo="abc" />);

    expect(
      screen.queryByRole("button", { name: /Eliminar partida/ }),
    ).not.toBeInTheDocument();
  });

  it("se muestra para usuarios autenticados", () => {
    useAuthStore.setState({ token: "t", user: USUARIO });
    renderConProviders(<EliminarPartidaButton codigo="abc" />);

    expect(
      screen.getByRole("button", { name: /Eliminar partida/ }),
    ).toBeInTheDocument();
  });

  it("pide confirmación antes de eliminar", async () => {
    const user = userEvent.setup();
    useAuthStore.setState({ token: "t", user: USUARIO });
    renderConProviders(<EliminarPartidaButton codigo="abc" />);

    await user.click(screen.getByRole("button", { name: /Eliminar partida/ }));
    expect(api.eliminarPartida).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /Confirmar eliminación/ }));
    await waitFor(() =>
      expect(api.eliminarPartida).toHaveBeenCalledWith("abc"),
    );
  });

  it("resetea el store al eliminar la partida activa", async () => {
    const user = userEvent.setup();
    useAuthStore.setState({ token: "t", user: USUARIO });
    usePartidaStore.getState().establecerCodigo("abc");
    renderConProviders(<EliminarPartidaButton codigo="abc" />);

    await user.click(screen.getByRole("button", { name: /Eliminar partida/ }));
    await user.click(screen.getByRole("button", { name: /Confirmar eliminación/ }));

    await waitFor(() =>
      expect(usePartidaStore.getState().codigoPartida).toBeNull(),
    );
  });
});
