"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Loader } from "@/components/ui/loader";
import { api, ApiClientError } from "@/lib/api";
import { usePartidaStore } from "@/store/partida-store";
import type { Genero } from "@/lib/types";

interface InicioDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const GENEROS: { value: Genero; label: string; emoji: string; descripcion: string }[] = [
  { value: "fantasía", label: "Fantasía", emoji: "🗡️", descripcion: "Magia, criaturas míticas, reinos antiguos." },
  { value: "ciencia ficción", label: "Ciencia ficción", emoji: "🚀", descripcion: "Naves, IA, futuros distantes." },
  { value: "terror", label: "Terror", emoji: "🕯️", descripcion: "Tensión psicológica, lo desconocido." },
];

export function InicioDialog({ open, onOpenChange }: InicioDialogProps) {
  const [genero, setGenero] = useState<Genero | null>(null);
  const [descripcion, setDescripcion] = useState("");
  const iniciarPartida = usePartidaStore((s) => s.iniciarPartida);

  const mutation = useMutation({
    mutationFn: ({ genero, descripcion }: { genero: Genero; descripcion: string }) =>
      api.iniciarPartida(genero, descripcion),
    onSuccess: (data) => {
      iniciarPartida({
        codigo: data.codigo_partida,
        personaje: data.personaje,
        objetivo: data.objetivo,
        primerTurno: {
          turno: data.primer_turno.turno,
          accion_jugador: "<inicio>",
          narrativa: data.primer_turno.narrativa,
          opciones: data.primer_turno.opciones,
          imagen_url: data.primer_turno.imagen_url,
        },
      });
      onOpenChange(false);
      setGenero(null);
      setDescripcion("");
    },
  });

  const puedeEnviar = genero !== null && descripcion.trim().length >= 10 && !mutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Nueva aventura</DialogTitle>
          <DialogDescription>
            Elegí un género y describí brevemente a tu personaje. La IA va a generar el mundo
            y la historia adaptándose a tus decisiones.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-5 py-2">
          <div className="grid gap-2">
            <Label>Género</Label>
            <div className="grid grid-cols-3 gap-2">
              {GENEROS.map((g) => (
                <button
                  key={g.value}
                  onClick={() => setGenero(g.value)}
                  disabled={mutation.isPending}
                  className={`p-3 rounded-md border-2 text-center transition-colors ${
                    genero === g.value
                      ? "border-primary bg-primary/10"
                      : "border-border hover:border-primary/50"
                  }`}
                >
                  <div className="text-2xl mb-1">{g.emoji}</div>
                  <div className="text-sm font-medium">{g.label}</div>
                </button>
              ))}
            </div>
            {genero && (
              <p className="text-xs text-muted-foreground italic">
                {GENEROS.find((g) => g.value === genero)?.descripcion}
              </p>
            )}
          </div>

          <div className="grid gap-2">
            <Label htmlFor="descripcion">Tu personaje</Label>
            <Textarea
              id="descripcion"
              placeholder="Ej: una arqueóloga escéptica de 40 años, especialista en ruinas perdidas..."
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
              disabled={mutation.isPending}
              maxLength={300}
              rows={3}
            />
            <p className="text-xs text-muted-foreground">
              {descripcion.length}/300 caracteres (mínimo 10)
            </p>
          </div>

          {mutation.isError && (
            <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
              {mutation.error instanceof ApiClientError
                ? mutation.error.message
                : "Error inesperado al crear la partida"}
            </div>
          )}
        </div>

        <DialogFooter>
          {mutation.isPending ? (
            <Loader message="Generando tu aventura..." />
          ) : (
            <Button
              onClick={() => genero && mutation.mutate({ genero, descripcion })}
              disabled={!puedeEnviar}
            >
              Comenzar aventura
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
