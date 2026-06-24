import { describe, expect, it, vi, beforeEach } from "vitest";
import { act, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import HomePage from "@/app/page";
import { usePartidaStore } from "@/store/partida-store";
import type { Tirada, TurnoHistorial } from "@/lib/types";

// El canvas 3D usa WebGL (ausente en jsdom): lo neutralizamos.
vi.mock("@/components/dice-3d-canvas", async () => {
  const React = await import("react");
  return { default: () => React.createElement("div", { "data-testid": "dice-canvas" }) };
});

const tirada: Tirada = {
  habilidad: "destreza",
  banda: "media",
  dc: 15,
  d20: 14,
  modificador: 3,
  total: 17,
  resultado: "exito",
};

const turno: TurnoHistorial = {
  turno: 1,
  accion_jugador: "<inicio>",
  narrativa: "Apertura.",
  opciones: ["a", "b", "c"],
  imagen_url: null,
  tirada: null,
};

function renderHome() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <HomePage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  usePartidaStore.getState().resetear();
});

describe("HomePage: el narrador no muestra texto crudo del stream", () => {
  it("no muestra narrativa mientras se genera el turno (sin turno pendiente)", () => {
    // Generación en curso: aunque hubiera texto parcial, no debe verse hasta el
    // revelado (turno pendiente). Esto evita el flash de la preparación (fase 1).
    act(() => {
      usePartidaStore.setState({
        codigoPartida: "abc",
        historial: [turno],
        estado: "en_curso",
        isStreaming: true,
        streamingNarrativa: "texto parcial del stream",
        tiradaActual: null,
        turnoPendiente: null,
      });
    });
    renderHome();

    expect(screen.queryByText("texto parcial del stream")).not.toBeInTheDocument();
    expect(screen.queryByText(/Generando/)).not.toBeInTheDocument();
  });

  it("oculta el narrador mientras el modal del dado está abierto", () => {
    act(() => {
      usePartidaStore.setState({
        codigoPartida: "abc",
        historial: [turno],
        estado: "en_curso",
        isStreaming: true,
        streamingNarrativa: "desenlace bufferizado",
        tiradaActual: tirada, // modal abierto
        turnoPendiente: {
          turno: { ...turno, turno: 2 },
          imagenPendiente: false,
          estadoFinal: null,
        },
      });
    });
    renderHome();

    expect(screen.queryByText("desenlace bufferizado")).not.toBeInTheDocument();
  });
});
