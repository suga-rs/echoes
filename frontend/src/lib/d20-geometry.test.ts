import { describe, expect, it } from "vitest";
import { VALORES_D20, quaternionParaValor } from "@/lib/d20-geometry";

function casiIguales(a: number[], b: number[], tol = 1e-3): boolean {
  return a.every((v, i) => Math.abs(v - b[i]) < tol);
}

describe("d20-geometry", () => {
  it("cubre los 20 valores", () => {
    expect(VALORES_D20).toHaveLength(20);
    expect(VALORES_D20[0]).toBe(1);
    expect(VALORES_D20[19]).toBe(20);
  });

  it("devuelve un quaternion unitario por valor", () => {
    for (const v of VALORES_D20) {
      const [x, y, z, w] = quaternionParaValor(v);
      const norma = Math.sqrt(x * x + y * y + z * z + w * w);
      expect(norma).toBeCloseTo(1, 3);
    }
  });

  it("cada cara mapea a una orientación distinta", () => {
    const quats = VALORES_D20.map(quaternionParaValor);
    for (let i = 0; i < quats.length; i++) {
      for (let j = i + 1; j < quats.length; j++) {
        expect(casiIguales(quats[i], quats[j])).toBe(false);
      }
    }
  });

  it("es determinista para el mismo valor", () => {
    expect(quaternionParaValor(14)).toEqual(quaternionParaValor(14));
  });
});
