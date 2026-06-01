import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { TurnoHistorial } from "@/lib/types";
import { TurnoCard } from "@/components/turno-card";

vi.mock("next/image", () => ({
  default: ({ src, alt }: { src: string; alt: string }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt} />
  ),
}));

vi.mock("@/lib/api", () => ({
  api: { generarImagenTurno: vi.fn() },
  ApiClientError: class ApiClientError extends Error {},
}));

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
});
