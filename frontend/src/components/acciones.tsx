"use client";

import { useState, type FormEvent } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader } from "@/components/ui/loader";
import { avanzarTurnoStream, ApiClientError } from "@/lib/api";
import { usePartidaStore } from "@/store/partida-store";

interface AccionesProps {
  opciones: string[];
}

export function Acciones({ opciones }: AccionesProps) {
  const [accionLibre, setAccionLibre] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  const codigo = usePartidaStore((s) => s.codigoPartida);
  const isStreaming = usePartidaStore((s) => s.isStreaming);
  const iniciarStreaming = usePartidaStore((s) => s.iniciarStreaming);
  const appendStreamToken = usePartidaStore((s) => s.appendStreamToken);
  const finalizarStreaming = usePartidaStore((s) => s.finalizarStreaming);
  const actualizarImagenTurno = usePartidaStore((s) => s.actualizarImagenTurno);
  const actualizarEstadoFinal = usePartidaStore((s) => s.actualizarEstadoFinal);
  const cancelarStreaming = usePartidaStore((s) => s.cancelarStreaming);

  const enviarAccion = async (accion: string) => {
    if (!accion.trim() || isStreaming || !codigo) return;

    setError(null);
    setIsPending(true);
    iniciarStreaming();

    let turnoNum = 0;

    await avanzarTurnoStream(codigo, accion.trim(), {
      onToken: (content) => appendStreamToken(content),

      onTurno: (data) => {
        turnoNum = data.turno;
        finalizarStreaming({
          turno: data.turno,
          accion_jugador: accion.trim(),
          narrativa: data.narrativa,
          opciones: data.opciones,
          imagen_url: null,
        }, data.imagen_pendiente);
        if (data.estado === "finalizada") {
          actualizarEstadoFinal(data.estado, data.final, data.razon_fin);
        }
        setAccionLibre("");
      },

      onImagen: (url) => actualizarImagenTurno(turnoNum, url),

      onError: (err) => {
        setError(err instanceof ApiClientError ? err.message : "Error inesperado");
        setIsPending(false);
        cancelarStreaming();
      },

      onDone: () => setIsPending(false),
    });
  };

  const onSubmitLibre = (e: FormEvent) => {
    e.preventDefault();
    void enviarAccion(accionLibre);
  };

  if (isStreaming) {
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
            onClick={() => void enviarAccion(opcion)}
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
          disabled={isPending}
        />
        <Button
          type="submit"
          size="icon"
          disabled={!accionLibre.trim() || isPending}
          aria-label="Enviar acción"
        >
          <Send className="h-4 w-4" />
        </Button>
      </form>

      {error && (
        <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
          {error}
        </div>
      )}
    </div>
  );
}
