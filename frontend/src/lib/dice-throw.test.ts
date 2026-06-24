import { describe, expect, it } from "vitest";
import * as THREE from "three";
import { quaternionParaValor } from "@/lib/d20-geometry";
import {
  CAM_REPOSO,
  DUR_FLIGHT,
  DUR_TOTAL,
  alturaEnT,
  camaraZEnT,
  crearParametros,
  estaAsentado,
  horizontalEnT,
  orientacionEnT,
  settleEmpieza,
} from "@/lib/dice-throw";

/** RNG determinista para reproducir tiradas en los tests. */
function rngFijo(seed: number): () => number {
  let s = seed;
  return () => {
    s = (s * 1664525 + 1013904223) % 0xffffffff;
    return s / 0xffffffff;
  };
}

describe("dice-throw", () => {
  it("la duración total es la suma de las fases y queda en un rango cómodo", () => {
    expect(DUR_TOTAL).toBeGreaterThanOrEqual(2);
    expect(DUR_TOTAL).toBeLessThanOrEqual(2.6);
  });

  it("la altura arranca y termina en el suelo", () => {
    expect(alturaEnT(0)).toBeCloseTo(0, 5);
    expect(alturaEnT(DUR_TOTAL)).toBeCloseTo(0, 5);
    expect(alturaEnT(DUR_TOTAL + 1)).toBeCloseTo(0, 5);
  });

  it("rebota dos veces con ápices decrecientes", () => {
    // Ápice del vuelo, del primer rebote y del segundo rebote (mitades de fase).
    const apexVuelo = alturaEnT(DUR_FLIGHT / 2);
    const apexRebote1 = alturaEnT(DUR_FLIGHT + 0.18);
    const apexRebote2 = alturaEnT(settleEmpieza() - 0.12);
    expect(apexVuelo).toBeGreaterThan(apexRebote1);
    expect(apexRebote1).toBeGreaterThan(apexRebote2);
    expect(apexRebote2).toBeGreaterThan(0);
  });

  it("se desplaza desde un lanzamiento descentrado hacia el centro", () => {
    expect(Math.abs(horizontalEnT(0))).toBeGreaterThan(0.3);
    expect(horizontalEnT(DUR_TOTAL)).toBeCloseTo(0, 2);
  });

  it("la cámara se aleja en pleno vuelo y vuelve al reposo al asentar", () => {
    expect(camaraZEnT(0)).toBeCloseTo(CAM_REPOSO, 5);
    expect(camaraZEnT(DUR_TOTAL)).toBeCloseTo(CAM_REPOSO, 5);
    expect(camaraZEnT(DUR_FLIGHT / 2)).toBeGreaterThan(CAM_REPOSO);
  });

  it("aterriza EXACTO en la cara del valor del servidor", () => {
    for (const valor of [1, 7, 14, 20]) {
      const params = crearParametros(valor, rngFijo(valor + 1));
      const final = orientacionEnT(DUR_TOTAL, params);
      const objetivo = new THREE.Quaternion(...quaternionParaValor(valor));
      expect(final.angleTo(objetivo)).toBeCloseTo(0, 4);
    }
  });

  it("la orientación es continua en la frontera vuelo→asentado (sin salto)", () => {
    const params = crearParametros(14, rngFijo(99));
    const t0 = settleEmpieza();
    const dt = 1e-3;
    // Salto angular justo en la frontera vs. el movimiento del mismo lapso dentro
    // del vuelo: si fuese un teletransporte (el viejo "snap"), la frontera daría
    // un salto muchísimo mayor. Continuo ⇒ del mismo orden de magnitud.
    const saltoFrontera = orientacionEnT(t0 - dt, params).angleTo(orientacionEnT(t0 + dt, params));
    const saltoVuelo = orientacionEnT(t0 - 3 * dt, params).angleTo(orientacionEnT(t0 - dt, params));
    expect(saltoFrontera).toBeLessThan(3 * saltoVuelo);
  });

  it("solo se considera asentado al completar la tirada", () => {
    expect(estaAsentado(0)).toBe(false);
    expect(estaAsentado(DUR_TOTAL - 0.05)).toBe(false);
    expect(estaAsentado(DUR_TOTAL)).toBe(true);
  });

  it("crearParametros es determinista para una misma semilla y eje unitario", () => {
    const a = crearParametros(14, rngFijo(5));
    const b = crearParametros(14, rngFijo(5));
    expect(a.ejeTumble.length()).toBeCloseTo(1, 5);
    expect(a.ejeTumble.equals(b.ejeTumble)).toBe(true);
  });
});
