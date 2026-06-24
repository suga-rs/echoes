import { describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";
import Dice3DCanvas from "@/components/dice-3d-canvas";

// jsdom no provee contexto WebGL, así que el componente cae al camino de
// respaldo: revela el resultado autoritativo invocando onSettled sin animar.
describe("Dice3DCanvas — respaldo sin WebGL", () => {
  it("invoca onSettled exactamente una vez cuando no hay WebGL", () => {
    const onSettled = vi.fn();
    render(<Dice3DCanvas valor={14} resultado="exito" rodar onSettled={onSettled} />);
    expect(onSettled).toHaveBeenCalledTimes(1);
  });

  it("revela el resultado aun en reposo (rodar=false) si no hay WebGL", () => {
    const onSettled = vi.fn();
    render(<Dice3DCanvas valor={20} resultado="exito_critico" rodar={false} onSettled={onSettled} />);
    expect(onSettled).toHaveBeenCalledTimes(1);
  });
});
