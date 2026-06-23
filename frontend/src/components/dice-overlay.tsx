"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { VisuallyHidden } from "@radix-ui/react-visually-hidden";
import { TiradaReveal } from "@/components/tirada-reveal";
import type { Tirada } from "@/lib/types";

// Three.js solo se carga cuando ocurre el primer check (no en el bundle inicial),
// y nunca en SSR (WebGL es client-only).
const Dice3DCanvas = dynamic(() => import("@/components/dice-3d-canvas"), {
  ssr: false,
  loading: () => null,
});

function prefiereMenosMovimiento(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

interface DiceOverlayProps {
  tirada: Tirada;
  onClose: () => void;
}

/**
 * Overlay full-screen de la tirada. La animación 3D es realce sobre el resultado
 * autoritativo del servidor; bajo reduced-motion (o si falla la carga) degrada al
 * revelado estático con los mismos valores. Auto-cierra dando paso a la narrativa.
 */
export function DiceOverlay({ tirada, onClose }: DiceOverlayProps) {
  const reducido = prefiereMenosMovimiento();
  // Con reduced-motion mostramos el resultado de una; con animación, recién al asentar.
  const [revelado, setRevelado] = useState(reducido);

  useEffect(() => {
    if (!revelado) return;
    // Sostener el resultado un instante y dar paso a la narrativa (fase 2).
    const id = setTimeout(onClose, reducido ? 1400 : 1600);
    return () => clearTimeout(id);
  }, [revelado, reducido, onClose]);

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-md border-0 bg-background/95 [&>button]:hidden">
        <VisuallyHidden>
          <DialogTitle>Tirada de dado</DialogTitle>
        </VisuallyHidden>

        {!reducido && (
          <div className="mx-auto h-48 w-48" aria-hidden>
            <Dice3DCanvas
              valor={tirada.d20}
              resultado={tirada.resultado}
              onSettled={() => setRevelado(true)}
            />
          </div>
        )}

        {revelado ? (
          <TiradaReveal tirada={tirada} />
        ) : (
          <p className="text-center text-sm text-muted-foreground">Tirando…</p>
        )}
      </DialogContent>
    </Dialog>
  );
}
