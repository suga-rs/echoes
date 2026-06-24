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
  it("muestra habilidad, dificultad y resultado, sin datos técnicos", () => {
    render(<TiradaReveal tirada={base} />);
    expect(screen.getByText(/Destreza/)).toBeInTheDocument();
    expect(screen.getByText(/Media/)).toBeInTheDocument();
    expect(screen.getByText("Éxito")).toBeInTheDocument();
    // Los números técnicos no se muestran al jugador.
    expect(screen.queryByText(/d20/)).not.toBeInTheDocument();
    expect(screen.queryByText(/DC/)).not.toBeInTheDocument();
  });

  it("distingue el éxito crítico", () => {
    render(<TiradaReveal tirada={{ ...base, d20: 20, resultado: "exito_critico" }} />);
    expect(screen.getByText("¡Éxito crítico!")).toBeInTheDocument();
  });

  it("muestra el fracaso sin exponer el cálculo", () => {
    render(<TiradaReveal tirada={{ ...base, modificador: -2, total: 12, resultado: "fracaso" }} />);
    expect(screen.getByText("Fracaso")).toBeInTheDocument();
    expect(screen.queryByText(/=/)).not.toBeInTheDocument();
  });
});
