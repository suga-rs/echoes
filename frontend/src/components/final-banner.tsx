"use client";

import { Trophy, Skull, CircleHelp } from "lucide-react";
import { Button } from "@/components/ui/button";

interface FinalBannerProps {
  final: "exito" | "fracaso" | "ambiguo" | null;
  razon: string | null;
  onNuevaPartida: () => void;
}

const ESTILOS = {
  exito: {
    Icon: Trophy,
    titulo: "Victoria",
    color: "text-green-700 dark:text-green-400",
    bg: "bg-green-50 dark:bg-green-950/30",
    border: "border-green-200 dark:border-green-900",
  },
  fracaso: {
    Icon: Skull,
    titulo: "La aventura terminó",
    color: "text-destructive",
    bg: "bg-destructive/10",
    border: "border-destructive/30",
  },
  ambiguo: {
    Icon: CircleHelp,
    titulo: "Final ambiguo",
    color: "text-muted-foreground",
    bg: "bg-muted",
    border: "border-border",
  },
};

export function FinalBanner({ final, razon, onNuevaPartida }: FinalBannerProps) {
  if (!final) return null;
  const { Icon, titulo, color, bg, border } = ESTILOS[final];

  return (
    <div
      className={`${bg} ${border} border-2 rounded-lg p-6 text-center animate-slide-up`}
    >
      <Icon className={`${color} h-12 w-12 mx-auto mb-3`} />
      <h2 className={`${color} text-2xl font-bold mb-2`}>{titulo}</h2>
      {razon && <p className="text-muted-foreground italic mb-4">{razon}</p>}
      <Button onClick={onNuevaPartida}>Empezar nueva aventura</Button>
    </div>
  );
}
