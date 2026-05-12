"use client";

import Image from "next/image";
import type { TurnoHistorial } from "@/lib/types";

interface TurnoCardProps {
  turno: TurnoHistorial;
  esUltimo: boolean;
}

export function TurnoCard({ turno, esUltimo }: TurnoCardProps) {
  return (
    <article className="animate-fade-in mb-8">
      {turno.accion_jugador !== "<inicio>" && (
        <div className="mb-4 flex justify-end">
          <div className="bg-primary/15 text-foreground px-4 py-2 rounded-2xl rounded-tr-sm max-w-[80%] text-sm">
            <span className="text-xs text-muted-foreground block mb-0.5">Tu acción:</span>
            {turno.accion_jugador}
          </div>
        </div>
      )}

      {turno.imagen_url && (
        <div className="relative w-full aspect-[3/2] mb-4 rounded-lg overflow-hidden bg-muted">
          <Image
            src={turno.imagen_url}
            alt={`Escena del turno ${turno.turno}`}
            fill
            className="object-cover"
            sizes="(max-width: 768px) 100vw, 768px"
            priority={esUltimo}
            unoptimized
          />
        </div>
      )}

      <div className="bg-card rounded-lg p-5 border">
        <div className="text-xs text-muted-foreground uppercase tracking-wide mb-2">
          Turno {turno.turno}
        </div>
        <p className="narrativa whitespace-pre-wrap">{turno.narrativa}</p>
      </div>
    </article>
  );
}
