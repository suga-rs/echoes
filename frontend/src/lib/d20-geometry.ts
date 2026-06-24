/**
 * Geometría del d20: para cada valor (1-20) calcula el quaternion que orienta
 * la cara correspondiente hacia la cámara (+Z). Es un lookup determinista
 * derivado de las normales del icosaedro, sin física. La animación frena en
 * este quaternion para que el dado caiga EXACTO en el valor que tiró el servidor.
 */
import * as THREE from "three";

// Icosaedro unitario (20 caras, detalle 0). PolyhedronGeometry produce posición
// no indexada: 20 caras * 3 vértices = 60 entradas, una tras otra por cara.
const _geometria = new THREE.IcosahedronGeometry(1, 0);
const _posicion = _geometria.getAttribute("position");

const _haciaCamara = new THREE.Vector3(0, 0, 1);

/** Centroide crudo de la cara `indice` sobre el icosaedro unitario (radio 1). Su
 * magnitud es el inradio (< 1); su dirección normalizada es la normal de la cara. */
function centroideDeCara(indice: number): THREE.Vector3 {
  const a = new THREE.Vector3().fromBufferAttribute(_posicion, indice * 3);
  const b = new THREE.Vector3().fromBufferAttribute(_posicion, indice * 3 + 1);
  const c = new THREE.Vector3().fromBufferAttribute(_posicion, indice * 3 + 2);
  return a.add(b).add(c).divideScalar(3);
}

function normalDeCara(indice: number): THREE.Vector3 {
  // En un icosaedro centrado en el origen, la dirección del centroide de la
  // cara coincide con su normal.
  return centroideDeCara(indice).normalize();
}

export type QuaternionTuple = [number, number, number, number];

/** Quaternion (x,y,z,w) que lleva la cara del `valor` (1-20) a mirar a la cámara. */
export function quaternionParaValor(valor: number): QuaternionTuple {
  const indice = ((valor - 1) % 20 + 20) % 20;
  const normal = normalDeCara(indice);
  const q = new THREE.Quaternion().setFromUnitVectors(normal, _haciaCamara);
  return [q.x, q.y, q.z, q.w];
}

export interface CaraD20 {
  /** Índice de cara 0-19. */
  indice: number;
  /** Valor numérico rotulado en la cara. Contrato: cara `i` ↔ valor `i + 1`,
   * consistente con {@link quaternionParaValor}. */
  valor: number;
  /** Centroide sobre el icosaedro unitario (radio 1). Escalá por el radio del
   * dado para ubicar el rótulo sobre la superficie. */
  centroide: THREE.Vector3;
  /** Normal unitaria de la cara (hacia afuera). */
  normal: THREE.Vector3;
}

/** Geometría por cara para colocar rótulos numéricos sobre el d20. */
export function carasD20(): CaraD20[] {
  return Array.from({ length: 20 }, (_, indice) => {
    const centroide = centroideDeCara(indice);
    return {
      indice,
      valor: indice + 1,
      centroide,
      normal: centroide.clone().normalize(),
    };
  });
}

export const VALORES_D20: number[] = Array.from({ length: 20 }, (_, i) => i + 1);
