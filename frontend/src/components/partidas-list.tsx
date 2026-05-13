"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Loader } from "@/components/ui/loader";

const GENERO_EMOJI: Record<string, string> = {
  "fantasía": "🗡️",
  "ciencia ficción": "🚀",
  "terror": "🕯️",
};

interface PartidasListProps {
  onReanudar: (codigo: string) => void;
}

export function PartidasList({ onReanudar }: PartidasListProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["partidas"],
    queryFn: () => api.listarPartidas(),
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <Loader message="Cargando partidas..." />
      </div>
    );
  }

  if (isError) {
    return (
      <p className="text-sm text-destructive py-4 text-center">
        Error al cargar las partidas. Intentá de nuevo.
      </p>
    );
  }

  if (!data || data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4 text-center">
        No hay partidas guardadas.
      </p>
    );
  }

  return (
    <ul className="space-y-3">
      {data.map((partida) => (
        <li
          key={partida.codigo_partida}
          className="flex items-center justify-between gap-4 rounded-lg border bg-card p-4"
        >
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-base">{GENERO_EMOJI[partida.genero] ?? "📖"}</span>
              <span className="font-medium truncate">{partida.nombre_personaje}</span>
              <span
                className={`ml-auto shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                  partida.estado === "en_curso"
                    ? "bg-green-500/15 text-green-700 dark:text-green-400"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {partida.estado === "en_curso" ? "En curso" : "Finalizada"}
              </span>
            </div>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span>Turno {partida.turno_actual}</span>
              <span className="font-mono">{partida.codigo_partida.slice(0, 9)}</span>
            </div>
          </div>
          <Button size="sm" variant="outline" onClick={() => onReanudar(partida.codigo_partida)}>
            Reanudar
          </Button>
        </li>
      ))}
    </ul>
  );
}
