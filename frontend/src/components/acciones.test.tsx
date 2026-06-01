import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Acciones } from "@/components/acciones";
import { usePartidaStore } from "@/store/partida-store";

vi.mock("@/lib/api", () => ({
  avanzarTurnoStream: vi.fn(),
  ApiClientError: class ApiClientError extends Error {},
}));

beforeEach(() => {
  usePartidaStore.getState().resetear();
});

describe("Acciones", () => {
  it("renderiza un botón por cada opción", () => {
    render(<Acciones opciones={["Mirar alrededor", "Correr", "Hablar con el guardia"]} />);

    expect(screen.getByRole("button", { name: /Mirar alrededor/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Correr/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Hablar con el guardia/ })).toBeInTheDocument();
  });

  it("el botón de enviar arranca deshabilitado y se habilita al tipear", async () => {
    const user = userEvent.setup();
    render(<Acciones opciones={["a", "b", "c"]} />);

    const enviar = screen.getByRole("button", { name: "Enviar acción" });
    expect(enviar).toBeDisabled();

    await user.type(screen.getByPlaceholderText(/tu propia acción/i), "abrir la puerta");

    expect(enviar).toBeEnabled();
  });
});
