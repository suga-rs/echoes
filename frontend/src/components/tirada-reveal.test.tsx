import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { TiradaReveal } from "@/components/tirada-reveal";
import type { Tirada } from "@/lib/types";

const base: Tirada = {
  habilidad: "destreza",
  banda: "media",
  dc: 15,
  d20: 14,
  modificador: 3,
  total: 17,
  resultado: "exito",
};

describe("TiradaReveal", () => {
  it("muestra habilidad, DC y el cálculo del total", () => {
    render(<TiradaReveal tirada={base} />);
    expect(screen.getByText(/Destreza/)).toBeInTheDocument();
    expect(screen.getByText(/d20 14 \+3 = 17 vs DC 15/)).toBeInTheDocument();
    expect(screen.getByText("Éxito")).toBeInTheDocument();
  });

  it("distingue el éxito crítico", () => {
    render(<TiradaReveal tirada={{ ...base, d20: 20, resultado: "exito_critico" }} />);
    expect(screen.getByText("¡Éxito crítico!")).toBeInTheDocument();
  });

  it("muestra modificador negativo con su signo", () => {
    render(<TiradaReveal tirada={{ ...base, modificador: -2, total: 12, resultado: "fracaso" }} />);
    expect(screen.getByText(/d20 14 -2 = 12/)).toBeInTheDocument();
  });
});
