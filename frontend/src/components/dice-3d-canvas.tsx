"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { ResultadoTirada } from "@/lib/types";
import { carasD20, quaternionParaValor } from "@/lib/d20-geometry";

const DUR_TUMBLE = 1.2; // s de giro caótico
const DUR_SETTLE = 0.7; // s de frenado hacia la cara objetivo
const RADIO = 1.3; // radio del icosaedro del dado

const EMISSIVE: Record<ResultadoTirada, number> = {
  exito_critico: 0xf59e0b, // dorado
  exito: 0x10b981, // esmeralda tenue
  fracaso: 0x1f2937, // gris
  fracaso_critico: 0xef4444, // rojo
};

interface Dice3DCanvasProps {
  valor: number;
  resultado: ResultadoTirada;
  /** Cuando pasa a `true`, el dado arranca la animación de tirada. Mientras es
   * `false`, el dado reposa apuntando la cara 20 a la cámara. */
  rodar: boolean;
  onSettled: () => void;
}

/** Textura de canvas con un número, para rotular una cara del d20. */
function texturaNumero(n: number): THREE.CanvasTexture {
  const size = 128;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    ctx.clearRect(0, 0, size, size);
    ctx.fillStyle = "#111827";
    ctx.font = "bold 76px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(String(n), size / 2, size / 2 + 4);
  }
  const tex = new THREE.CanvasTexture(canvas);
  tex.anisotropy = 4;
  return tex;
}

/** Crea los 20 planos numerados, parentados al dado para que giren con él. */
function construirRotulos(): { grupo: THREE.Group; dispose: () => void } {
  const grupo = new THREE.Group();
  const texturas: THREE.CanvasTexture[] = [];
  const geometrias: THREE.PlaneGeometry[] = [];
  const materiales: THREE.MeshBasicMaterial[] = [];
  const ejeZ = new THREE.Vector3(0, 0, 1);

  for (const cara of carasD20()) {
    const tex = texturaNumero(cara.valor);
    const geo = new THREE.PlaneGeometry(0.62, 0.62);
    const mat = new THREE.MeshBasicMaterial({
      map: tex,
      transparent: true,
      depthWrite: false,
    });
    const plano = new THREE.Mesh(geo, mat);
    // Apoyado sobre la cara (centroide escalado al radio), con un mínimo offset
    // hacia afuera para evitar z-fighting, orientado a lo largo de la normal.
    plano.position
      .copy(cara.centroide)
      .multiplyScalar(RADIO)
      .addScaledVector(cara.normal, 0.012);
    plano.quaternion.setFromUnitVectors(ejeZ, cara.normal);
    grupo.add(plano);
    texturas.push(tex);
    geometrias.push(geo);
    materiales.push(mat);
  }

  return {
    grupo,
    dispose: () => {
      texturas.forEach((t) => t.dispose());
      geometrias.forEach((g) => g.dispose());
      materiales.forEach((m) => m.dispose());
    },
  };
}

/**
 * d20 3D en three.js puro (sin react-three-fiber). Reposa apuntando la cara 20 a
 * la cámara y, al activarse (`rodar`), rueda y frena en la cara del valor que tiró
 * el servidor. La animación es solo realce: el resultado autoritativo es del server.
 */
export default function Dice3DCanvas({ valor, resultado, rodar, onSettled }: Dice3DCanvasProps) {
  const contenedor = useRef<HTMLDivElement>(null);
  // Refs para que cambios de identidad del callback o del flag no recreen la escena.
  const onSettledRef = useRef(onSettled);
  onSettledRef.current = onSettled;
  const rodarRef = useRef(rodar);
  rodarRef.current = rodar;

  useEffect(() => {
    const cont = contenedor.current;
    if (!cont) return;
    const w = cont.clientWidth || 192;
    const h = cont.clientHeight || 192;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      // Sin WebGL: revelamos el resultado igual (la animación es solo realce).
      onSettledRef.current();
      return;
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(w, h);
    cont.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
    camera.position.set(0, 0, 4);

    scene.add(new THREE.AmbientLight(0xffffff, 0.7));
    const luz = new THREE.DirectionalLight(0xffffff, 1.2);
    luz.position.set(3, 4, 5);
    scene.add(luz);

    const esCritico = resultado === "exito_critico" || resultado === "fracaso_critico";
    const geometria = new THREE.IcosahedronGeometry(RADIO, 0);
    const material = new THREE.MeshStandardMaterial({
      color: 0xe5e7eb,
      flatShading: true,
      metalness: 0.3,
      roughness: 0.4,
      emissive: new THREE.Color(EMISSIVE[resultado]),
      emissiveIntensity: 0.1,
    });
    const mesh = new THREE.Mesh(geometria, material);
    const rotulos = construirRotulos();
    mesh.add(rotulos.grupo);
    scene.add(mesh);

    const [qx, qy, qz, qw] = quaternionParaValor(valor);
    const objetivo = new THREE.Quaternion(qx, qy, qz, qw);
    const [vx, vy, vz, vw] = quaternionParaValor(20);
    const reposo = new THREE.Quaternion(vx, vy, vz, vw);
    const desde = new THREE.Quaternion().setFromEuler(
      new THREE.Euler(valor * 1.7, valor * 2.3, valor * 0.9),
    );

    // Pose de reposo: cara 20 hacia la cámara, sin animar hasta que `rodar` sea true.
    mesh.quaternion.copy(reposo);

    let raf = 0;
    let t = 0;
    let last = performance.now();
    let avisado = false;
    let rodando = false;

    const loop = (now: number) => {
      const delta = (now - last) / 1000;
      last = now;

      if (rodarRef.current) {
        if (!rodando) {
          // Arranque de la tirada: reseteamos el cronómetro de la animación.
          rodando = true;
          t = 0;
        }
        t += delta;

        if (t < DUR_TUMBLE) {
          // Giro rápido multiaxis (el "tumble").
          mesh.rotation.x += delta * 9;
          mesh.rotation.y += delta * 7;
          mesh.rotation.z += delta * 5;
        } else {
          // Settle: interpolamos hacia la cara objetivo (easeOutCubic).
          const p = Math.min(1, (t - DUR_TUMBLE) / DUR_SETTLE);
          const ease = 1 - Math.pow(1 - p, 3);
          mesh.quaternion.slerpQuaternions(desde, objetivo, ease);
          if (p >= 1 && !avisado) {
            avisado = true;
            material.emissiveIntensity = esCritico ? 0.9 : 0.35;
            onSettledRef.current();
          }
        }
      }
      // En reposo (rodar=false) el dado queda quieto apuntando la cara 20.

      renderer.render(scene, camera);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(raf);
      rotulos.dispose();
      geometria.dispose();
      material.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode === cont) {
        cont.removeChild(renderer.domElement);
      }
    };
  }, [valor, resultado]);

  return <div ref={contenedor} className="h-full w-full" aria-hidden />;
}
