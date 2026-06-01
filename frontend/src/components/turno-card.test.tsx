import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/lib/api";
import type { TurnoHistorial } from "@/lib/types";
import { TurnoCard } from "@/components/turno-card";
import { usePartidaStore } from "@/store/partida-store";

vi.mock("next/image", () => ({
  default: ({ src, alt }: { src: string; alt: string }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt} />
  ),
}));

vi.mock("@/lib/api", () => ({
  api: {
    generarImagenTurno: vi.fn(),
    marcarFeedback: vi.fn().mockResolvedValue({ feedback: "incoherente" }),
  },
  ApiClientError: class ApiClientError extends Error {},
}));

beforeEach(() => {
  vi.clearAllMocks();
  usePartidaStore.getState().resetear();
});

const base: TurnoHistorial = {
  turno: 3,
  accion_jugador: "abrir la puerta",
  narrativa: "La puerta cruje al abrirse.",
  opciones: ["a", "b", "c"],
  imagen_url: null,
};

describe("TurnoCard", () => {
  it("renderiza la narrativa y el número de turno", () => {
    render(<TurnoCard turno={base} esUltimo={false} />);

    expect(screen.getByText("La puerta cruje al abrirse.")).toBeInTheDocument();
    expect(screen.getByText(/Turno 3/)).toBeInTheDocument();
  });

  it("muestra la acción del jugador salvo en el turno <inicio>", () => {
    const { rerender } = render(<TurnoCard turno={base} esUltimo={false} />);
    expect(screen.getByText("abrir la puerta")).toBeInTheDocument();

    rerender(<TurnoCard turno={{ ...base, accion_jugador: "<inicio>" }} esUltimo={false} />);
    expect(screen.queryByText("<inicio>")).not.toBeInTheDocument();
  });

  it("ofrece generar imagen cuando el turno no tiene imagen_url", () => {
    render(<TurnoCard turno={base} esUltimo={false} />);

    expect(screen.getByRole("button", { name: /Generar imagen/ })).toBeInTheDocument();
  });

  it("marca el turno como incoherente llamando a la API", async () => {
    const user = userEvent.setup();
    usePartidaStore.getState().establecerCodigo("abc-123");
    render(<TurnoCard turno={base} esUltimo={false} />);

    await user.click(screen.getByRole("button", { name: /Marcar turno como incoherente/ }));

    expect(api.marcarFeedback).toHaveBeenCalledWith("abc-123", 3);
  });
});
