import { describe, expect, it } from "vitest";
import * as THREE from "three";
import { VALORES_D20, carasD20, quaternionParaValor } from "@/lib/d20-geometry";

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

  it("expone las 20 caras con normal unitaria y valor i+1", () => {
    const caras = carasD20();
    expect(caras).toHaveLength(20);
    caras.forEach((cara, i) => {
      expect(cara.indice).toBe(i);
      expect(cara.valor).toBe(i + 1);
      expect(cara.normal.length()).toBeCloseTo(1, 3);
      // El centroide está a la distancia del inradio (< 1) del centro.
      expect(cara.centroide.length()).toBeGreaterThan(0);
      expect(cara.centroide.length()).toBeLessThan(1);
    });
  });

  it("la cara mirando a la cámara tras quaternionParaValor(v) rotula v", () => {
    const caras = carasD20();
    for (const v of VALORES_D20) {
      const [x, y, z, w] = quaternionParaValor(v);
      const q = new THREE.Quaternion(x, y, z, w);
      // La normal de la cara del valor v debe quedar apuntando a +Z (a cámara).
      const normalRotada = caras[v - 1].normal.clone().applyQuaternion(q);
      expect(normalRotada.x).toBeCloseTo(0, 3);
      expect(normalRotada.y).toBeCloseTo(0, 3);
      expect(normalRotada.z).toBeCloseTo(1, 3);
    }
  });
});
