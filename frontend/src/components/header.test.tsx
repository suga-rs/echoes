import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Header } from "@/components/header";
import { useAuthStore } from "@/store/auth-store";
import { usePartidaStore } from "@/store/partida-store";

// Hijos pesados: no aportan al comportamiento del menú.
vi.mock("@/components/auth-modal", () => ({
  AuthModal: () => null,
}));
vi.mock("@/components/settings-sheet", () => ({
  SettingsSheet: ({ open }: { open: boolean }) =>
    open ? <div data-testid="settings-sheet" /> : null,
}));
vi.mock("next/link", () => ({
  // Reenvía props extra (role, id, data-*) como hace next/link real: Radix los
  // inyecta vía `asChild`/Slot para marcar el ancla como menuitem.
  default: ({
    href,
    children,
    ...props
  }: {
    href: string;
    children: React.ReactNode;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

function renderHeader() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <Header onNuevaPartida={() => {}} />
    </QueryClientProvider>,
  );
}

const usuario = {
  id: "u1",
  username: "aragorn",
  creada_en: "2026-01-01",
  avatar_url: null,
};

beforeEach(() => {
  usePartidaStore.getState().resetear();
});

afterEach(() => {
  useAuthStore.setState({ token: null, user: null });
});

describe("Header — menú de usuario", () => {
  it("con sesión: el usuario abre un menú con perfil, ajustes y cerrar sesión", async () => {
    const user = userEvent.setup();
    useAuthStore.setState({ token: "t", user: usuario });
    renderHeader();

    await user.click(screen.getByRole("button", { name: /aragorn/ }));

    expect(screen.getByRole("menuitem", { name: /Ir al perfil/ })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /Ajustes/ })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /Cerrar sesión/ })).toBeInTheDocument();
  });

  it("con sesión: no hay botón de cerrar sesión fuera del menú", () => {
    useAuthStore.setState({ token: "t", user: usuario });
    renderHeader();

    expect(
      screen.queryByRole("button", { name: "Cerrar sesión" }),
    ).not.toBeInTheDocument();
  });

  it("con sesión: 'Ajustes' vive en el menú, no como engranaje suelto", async () => {
    const user = userEvent.setup();
    useAuthStore.setState({ token: "t", user: usuario });
    renderHeader();

    expect(screen.queryByRole("button", { name: "Ajustes" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /aragorn/ }));
    await user.click(screen.getByRole("menuitem", { name: /Ajustes/ }));

    expect(screen.getByTestId("settings-sheet")).toBeInTheDocument();
  });

  it("sin sesión: el engranaje de ajustes sigue disponible directamente", () => {
    renderHeader();

    expect(screen.getByRole("button", { name: "Ajustes" })).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /aragorn/ }),
    ).not.toBeInTheDocument();
  });
});
