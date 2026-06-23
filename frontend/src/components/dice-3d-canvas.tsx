"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { ResultadoTirada } from "@/lib/types";
import { quaternionParaValor } from "@/lib/d20-geometry";

const DUR_TUMBLE = 1.2; // s de giro caótico
const DUR_SETTLE = 0.7; // s de frenado hacia la cara objetivo

const EMISSIVE: Record<ResultadoTirada, number> = {
  exito_critico: 0xf59e0b, // dorado
  exito: 0x10b981, // esmeralda tenue
  fracaso: 0x1f2937, // gris
  fracaso_critico: 0xef4444, // rojo
};

interface Dice3DCanvasProps {
  valor: number;
  resultado: ResultadoTirada;
  onSettled: () => void;
}

/**
 * d20 3D en three.js puro (sin react-three-fiber): rueda y frena en la cara del
 * valor que tiró el servidor. Vanilla three evita el acoplamiento del reconciler
 * de r3f con los internals de React bajo el bundler de Next.
 */
export default function Dice3DCanvas({ valor, resultado, onSettled }: Dice3DCanvasProps) {
  const contenedor = useRef<HTMLDivElement>(null);
  // Ref para no recrear la escena si cambia la identidad del callback.
  const onSettledRef = useRef(onSettled);
  onSettledRef.current = onSettled;

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
    const geometria = new THREE.IcosahedronGeometry(1.3, 0);
    const material = new THREE.MeshStandardMaterial({
      color: 0xe5e7eb,
      flatShading: true,
      metalness: 0.3,
      roughness: 0.4,
      emissive: new THREE.Color(EMISSIVE[resultado]),
      emissiveIntensity: 0.1,
    });
    const mesh = new THREE.Mesh(geometria, material);
    scene.add(mesh);

    const [qx, qy, qz, qw] = quaternionParaValor(valor);
    const objetivo = new THREE.Quaternion(qx, qy, qz, qw);
    const desde = new THREE.Quaternion().setFromEuler(
      new THREE.Euler(valor * 1.7, valor * 2.3, valor * 0.9),
    );

    let raf = 0;
    let t = 0;
    let last = performance.now();
    let avisado = false;

    const loop = (now: number) => {
      const delta = (now - last) / 1000;
      last = now;
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

      renderer.render(scene, camera);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(raf);
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
