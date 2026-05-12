"use client";

import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader } from "@/components/ui/loader";
import { api, ApiClientError } from "@/lib/api";
import { usePartidaStore } from "@/store/partida-store";

interface AccionesProps {
  opciones: string[];
}

export function Acciones({ opciones }: AccionesProps) {
  const [accionLibre, setAccionLibre] = useState("");
  const codigo = usePartidaStore((s) => s.codigoPartida);
  const agregarTurno = usePartidaStore((s) => s.agregarTurno);
  const actualizarEstadoFinal = usePartidaStore((s) => s.actualizarEstadoFinal);

  const mutation = useMutation({
    mutationFn: ({ accion }: { accion: string }) => {
      if (!codigo) throw new Error("No hay partida activa");
      return api.avanzarTurno(codigo, accion);
    },
    onSuccess: (data, vars) => {
      agregarTurno({
        turno: data.turno,
        accion_jugador: vars.accion,
        narrativa: data.narrativa,
        opciones: data.opciones,
        imagen_url: data.imagen_url,
      });
      if (data.estado === "finalizada") {
        actualizarEstadoFinal(data.estado, data.final, data.razon_fin);
      }
      setAccionLibre("");
    },
  });

  const enviarAccion = (accion: string) => {
    if (!accion.trim() || mutation.isPending) return;
    mutation.mutate({ accion: accion.trim() });
  };

  const onSubmitLibre = (e: FormEvent) => {
    e.preventDefault();
    enviarAccion(accionLibre);
  };

  if (mutation.isPending) {
    return (
      <div className="bg-card rounded-lg p-5 border">
        <Loader message="La aventura continúa..." />
      </div>
    );
  }

  return (
    <div className="bg-card rounded-lg p-5 border space-y-3">
      <div className="text-xs text-muted-foreground uppercase tracking-wide">
        ¿Qué hacés?
      </div>

      <div className="grid gap-2">
        {opciones.map((opcion, idx) => (
          <Button
            key={idx}
            variant="outline"
            className="justify-start text-left h-auto py-3 whitespace-normal"
            onClick={() => enviarAccion(opcion)}
          >
            <span className="text-muted-foreground mr-3">{idx + 1}.</span>
            {opcion}
          </Button>
        ))}
      </div>

      <form onSubmit={onSubmitLibre} className="flex gap-2 pt-1">
        <Input
          placeholder="...o escribí tu propia acción"
          value={accionLibre}
          onChange={(e) => setAccionLibre(e.target.value)}
          maxLength={200}
        />
        <Button
          type="submit"
          size="icon"
          disabled={!accionLibre.trim()}
          aria-label="Enviar acción"
        >
          <Send className="h-4 w-4" />
        </Button>
      </form>

      {mutation.isError && (
        <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
          {mutation.error instanceof ApiClientError
            ? mutation.error.message
            : "Error inesperado"}
        </div>
      )}
    </div>
  );
}
