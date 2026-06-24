import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DiceOverlay } from "@/components/dice-overlay";
import type { Tirada } from "@/lib/types";

// Stub del canvas 3D (WebGL no existe en jsdom): asienta cuando arranca la tirada.
vi.mock("@/components/dice-3d-canvas", async () => {
  const React = await import("react");
  const DiceCanvasMock = ({ rodar, onSettled }: { rodar: boolean; onSettled: () => void }) => {
    React.useEffect(() => {
      if (rodar) onSettled();
    }, [rodar, onSettled]);
    return React.createElement("div", { "data-testid": "dice-canvas" });
  };
  return { default: DiceCanvasMock };
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

describe("DiceOverlay", () => {
  it("reposa sin animar ni revelar hasta que el jugador toca el dado", async () => {
    render(<DiceOverlay tirada={tirada} onClose={vi.fn()} />);
    await screen.findByTestId("dice-canvas");

    expect(screen.getByText("Tocá el dado para tirar")).toBeInTheDocument();
    // Sin tocar: no se reveló el resultado autoritativo.
    expect(screen.queryByText(/d20 14/)).not.toBeInTheDocument();
  });

  it("al tocar el dado, anima y revela el resultado del servidor", async () => {
    render(<DiceOverlay tirada={tirada} onClose={vi.fn()} />);
    const area = await screen.findByRole("button", { name: "Tocá el dado para tirar" });

    fireEvent.click(area);

    // Tras asentar, se revela el desenlace (habilidad + resultado), sin números técnicos.
    expect(await screen.findByText(/Destreza/)).toBeInTheDocument();
    expect(screen.getByText("Éxito")).toBeInTheDocument();
    expect(screen.queryByText(/d20/)).not.toBeInTheDocument();
  });

  it("no se auto-cierra: onClose no se invoca solo", async () => {
    const onClose = vi.fn();
    render(<DiceOverlay tirada={tirada} onClose={onClose} />);
    await screen.findByTestId("dice-canvas");

    await new Promise((r) => setTimeout(r, 60));
    expect(onClose).not.toHaveBeenCalled();
  });

  it("se cierra con el control de cierre del modal", async () => {
    const onClose = vi.fn();
    render(<DiceOverlay tirada={tirada} onClose={onClose} />);
    await screen.findByTestId("dice-canvas");

    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
