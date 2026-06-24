/**
 * Matemática pura (cerrada, sin estado ni WebGL) de la tirada del d20 como un
 * dado *lanzado*: vuela en un arco parabólico, rebota dos veces con energía
 * decreciente y se asienta EXACTO en la cara del valor que tiró el servidor.
 *
 * Todo es función del tiempo transcurrido `t` (segundos), así que es
 * independiente del frame-rate y testeable sin renderizar. El componente
 * `dice-3d-canvas` solo lee estas funciones cada frame y las aplica a la malla
 * y a la cámara.
 */
import * as THREE from "three";
import { quaternionParaValor } from "@/lib/d20-geometry";

// --- Duraciones de cada fase (s). Sintonizables sin tocar la estructura. ---
export const DUR_FLIGHT = 0.9; // arco de lanzamiento (sube y cae)
export const DUR_BOUNCE_1 = 0.55; // primer rebote
export const DUR_BOUNCE_2 = 0.4; // segundo rebote
export const DUR_SETTLE = 0.4; // alineación final a la cara objetivo
export const DUR_TOTAL = DUR_FLIGHT + DUR_BOUNCE_1 + DUR_BOUNCE_2 + DUR_SETTLE;

// --- Forma del lanzamiento ---
export const RESTITUCION = 0.45; // cada rebote alcanza este factor del ápice previo
const LAUNCH_APEX = 1.4; // altura máxima del arco de vuelo
const LAUNCH_X = -1.0; // desplazamiento horizontal inicial (descentrado)
const OMEGA_INICIAL = 22; // rad/s de tumble al lanzar
const OMEGA_FINAL = 6; // rad/s al borde del asentamiento

// --- Cámara (dolly para que el arco entre en el canvas) ---
export const CAM_REPOSO = 4; // z en reposo y al asentar
const CAM_LEJOS = 6.8; // z máximo en pleno vuelo

/** Instante en que arranca la fase de asentamiento. */
export function settleEmpieza(): number {
  return DUR_TOTAL - DUR_SETTLE;
}

/** Parábola normalizada que sube de 0 al ápice `apex` y vuelve a 0. */
function parabola(progreso: number, apex: number): number {
  const p = Math.min(1, Math.max(0, progreso));
  return apex * 4 * p * (1 - p);
}

function easeOutCubic(p: number): number {
  const x = Math.min(1, Math.max(0, p));
  return 1 - Math.pow(1 - x, 3);
}

/** Altura (y) del dado: arco de vuelo + dos rebotes decrecientes; 0 en reposo. */
export function alturaEnT(t: number): number {
  if (t <= 0) return 0;
  if (t < DUR_FLIGHT) {
    return parabola(t / DUR_FLIGHT, LAUNCH_APEX);
  }
  const tRebote1 = t - DUR_FLIGHT;
  if (tRebote1 < DUR_BOUNCE_1) {
    return parabola(tRebote1 / DUR_BOUNCE_1, LAUNCH_APEX * RESTITUCION);
  }
  const tRebote2 = tRebote1 - DUR_BOUNCE_1;
  if (tRebote2 < DUR_BOUNCE_2) {
    return parabola(tRebote2 / DUR_BOUNCE_2, LAUNCH_APEX * RESTITUCION * RESTITUCION);
  }
  return 0; // asentado en el suelo
}

/** Desplazamiento horizontal (x): del lanzamiento descentrado hacia el centro. */
export function horizontalEnT(t: number): number {
  const p = easeOutCubic(t / settleEmpieza());
  return LAUNCH_X * (1 - p);
}

/** z de la cámara: se aleja en vuelo (cabe el arco) y vuelve al reposo al asentar. */
export function camaraZEnT(t: number): number {
  const ts = settleEmpieza();
  if (t <= 0 || t >= ts) return CAM_REPOSO;
  const campana = Math.sin(Math.PI * (t / ts)); // 0 en los extremos, 1 al medio
  return CAM_REPOSO + (CAM_LEJOS - CAM_REPOSO) * campana;
}

/** Ángulo de tumble acumulado: velocidad angular que decae linealmente. */
function anguloTumble(t: number): number {
  const ts = settleEmpieza();
  const tc = Math.min(t, ts);
  // ω(τ) = ω0 + (ωf-ω0)·τ/ts  ⇒  θ(t) = ω0·t + (ωf-ω0)·t²/(2·ts)
  return OMEGA_INICIAL * tc + ((OMEGA_FINAL - OMEGA_INICIAL) * tc * tc) / (2 * ts);
}

export interface ParametrosTirada {
  /** Valor autoritativo del servidor (1-20). */
  valor: number;
  /** Eje unitario del tumble en vuelo (aleatorio por tirada). */
  ejeTumble: THREE.Vector3;
  /** Orientación inicial (reposo: cara 20 a cámara). */
  qInicial: THREE.Quaternion;
  /** Orientación objetivo: cara `valor` a cámara. */
  qObjetivo: THREE.Quaternion;
}

/** Vector unitario uniforme a partir de un RNG [0,1). */
function ejeAleatorio(rng: () => number): THREE.Vector3 {
  const theta = 2 * Math.PI * rng();
  const z = 2 * rng() - 1;
  const r = Math.sqrt(Math.max(0, 1 - z * z));
  return new THREE.Vector3(r * Math.cos(theta), r * Math.sin(theta), z);
}

/** Construye los parámetros de una tirada (eje de tumble aleatorio, poses fijas). */
export function crearParametros(valor: number, rng: () => number = Math.random): ParametrosTirada {
  return {
    valor,
    ejeTumble: ejeAleatorio(rng),
    qInicial: new THREE.Quaternion(...quaternionParaValor(20)),
    qObjetivo: new THREE.Quaternion(...quaternionParaValor(valor)),
  };
}

/**
 * Orientación del dado en `t`. En vuelo gira en forma continua (cerrada) sobre
 * `ejeTumble`; en la fase final hace slerp desde la orientación de vuelo (en la
 * frontera) hacia `qObjetivo`, llegando EXACTO a la cara objetivo al completar.
 * No hay teletransporte: ambas ramas coinciden en la frontera.
 */
export function orientacionEnT(t: number, p: ParametrosTirada): THREE.Quaternion {
  const ts = settleEmpieza();
  const tumble = (angulo: number) =>
    new THREE.Quaternion()
      .setFromAxisAngle(p.ejeTumble, angulo)
      .premultiply(p.qInicial);

  if (t <= ts) {
    return tumble(anguloTumble(t));
  }
  const qFrontera = tumble(anguloTumble(ts));
  const ease = easeOutCubic((t - ts) / DUR_SETTLE);
  return qFrontera.clone().slerp(p.qObjetivo, ease);
}

/** Escala de squash/stretch transitoria en cada impacto (1,1,1 fuera de impacto). */
export function escalaImpactoEnT(t: number): THREE.Vector3 {
  const impactos = [DUR_FLIGHT, DUR_FLIGHT + DUR_BOUNCE_1, DUR_TOTAL];
  const ventana = 0.12;
  let pulso = 0;
  for (const ti of impactos) {
    const d = Math.abs(t - ti);
    if (d < ventana) pulso = Math.max(pulso, 1 - d / ventana);
  }
  const amp = 0.18 * pulso;
  return new THREE.Vector3(1 + amp * 0.5, 1 - amp, 1 + amp * 0.5);
}

/** El dado quedó asentado (tirada completa) en `t`. */
export function estaAsentado(t: number): boolean {
  return t >= DUR_TOTAL;
}
