import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { DiceOverlay } from "@/components/dice-overlay";
import type { Tirada } from "@/lib/types";

const tirada: Tirada = {
  habilidad: "destreza",
  banda: "media",
  dc: 15,
  d20: 14,
  modificador: 3,
  total: 17,
  resultado: "exito",
};

function stubReducedMotion(reduce: boolean) {
  vi.stubGlobal(
    "matchMedia",
    vi.fn().mockImplementation((query: string) => ({
      matches: reduce,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("DiceOverlay (reduced motion)", () => {
  it("muestra los valores de la tirada del servidor sin montar el canvas 3D", () => {
    stubReducedMotion(true);
    const { container } = render(<DiceOverlay tirada={tirada} onClose={vi.fn()} />);

    // El resultado autoritativo se muestra como texto (assert data, no píxeles).
    expect(screen.getByText(/d20 14 \+3 = 17 vs DC 15/)).toBeInTheDocument();
    expect(screen.getByText("Éxito")).toBeInTheDocument();
    // Sin animación: no se montó ningún <canvas>.
    expect(container.querySelector("canvas")).toBeNull();
  });

  it("auto-cierra tras sostener el resultado", () => {
    vi.useFakeTimers();
    stubReducedMotion(true);
    const onClose = vi.fn();
    render(<DiceOverlay tirada={tirada} onClose={onClose} />);

    expect(onClose).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1500);
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
