"use client";

import { useState } from "react";
import Image from "next/image";
import type { TurnoHistorial } from "@/lib/types";
import { ImagenModal } from "@/components/imagen-modal";

interface TurnoCardProps {
  turno: TurnoHistorial;
  esUltimo: boolean;
  imagenCargando?: boolean;
}

export function TurnoCard({ turno, esUltimo, imagenCargando = false }: TurnoCardProps) {
  const [imagenAbierta, setImagenAbierta] = useState(false);

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

      {turno.imagen_url ? (
        <>
          <button
            type="button"
            onClick={() => setImagenAbierta(true)}
            className="relative w-full aspect-[3/2] mb-4 rounded-lg overflow-hidden bg-muted cursor-pointer hover:opacity-90 transition-opacity block"
          >
            <Image
              src={turno.imagen_url}
              alt={`Escena del turno ${turno.turno}`}
              fill
              className="object-cover"
              sizes="(max-width: 768px) 100vw, 768px"
              priority={esUltimo}
              unoptimized
            />
          </button>
          <ImagenModal
            src={turno.imagen_url}
            open={imagenAbierta}
            onClose={() => setImagenAbierta(false)}
            alt={`Escena del turno ${turno.turno}`}
          />
        </>
      ) : imagenCargando ? (
        <div className="w-full aspect-[3/2] mb-4 rounded-lg bg-muted animate-pulse" />
      ) : null}

      <div className="bg-card rounded-lg p-5 border">
        <div className="text-xs text-muted-foreground uppercase tracking-wide mb-2">
          Turno {turno.turno}
        </div>
        <p className="narrativa whitespace-pre-wrap">{turno.narrativa}</p>
      </div>
    </article>
  );
}

interface StreamingTurnoCardProps {
  narrativa: string;
}

export function StreamingTurnoCard({ narrativa }: StreamingTurnoCardProps) {
  return (
    <article className="mb-8">
      <div className="bg-card rounded-lg p-5 border">
        <div className="text-xs text-muted-foreground uppercase tracking-wide mb-2">
          Generando...
        </div>
        <p className="narrativa whitespace-pre-wrap">
          {narrativa}
          <span className="inline-block w-0.5 h-4 bg-foreground ml-0.5 align-text-bottom animate-pulse" />
        </p>
      </div>
    </article>
  );
}
