"use client";

import { useState } from "react";
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

interface DiceOverlayProps {
  tirada: Tirada;
  onClose: () => void;
}

/**
 * Overlay de la tirada. El dado reposa apuntando la cara 20 y solo rueda cuando
 * el jugador lo toca; tras asentar, el modal queda abierto hasta que el jugador
 * lo cierra (botón o click afuera). La narrativa se revela recién al cerrarlo.
 */
export function DiceOverlay({ tirada, onClose }: DiceOverlayProps) {
  const [rodar, setRodar] = useState(false);
  const [revelado, setRevelado] = useState(false);

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-md border-0 bg-background/95">
        <VisuallyHidden>
          <DialogTitle>Tirada de dado</DialogTitle>
        </VisuallyHidden>

        <button
          type="button"
          onClick={() => { if (!rodar) setRodar(true); }}
          disabled={rodar}
          aria-label={rodar ? "Dado en juego" : "Tocá el dado para tirar"}
          className="mx-auto block h-48 w-48 rounded-full focus:outline-none disabled:cursor-default enabled:cursor-pointer"
        >
          <Dice3DCanvas
            valor={tirada.d20}
            resultado={tirada.resultado}
            rodar={rodar}
            onSettled={() => setRevelado(true)}
          />
        </button>

        {!rodar && (
          <p className="text-center text-sm font-medium text-foreground/90 animate-pulse">
            Tocá el dado para tirar
          </p>
        )}

        {rodar && !revelado && (
          <p className="text-center text-sm text-muted-foreground">Tirando…</p>
        )}

        {revelado && <TiradaReveal tirada={tirada} />}
      </DialogContent>
    </Dialog>
  );
}
