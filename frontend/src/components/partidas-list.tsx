"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader } from "@/components/ui/loader";
import { EliminarPartidaButton } from "@/components/eliminar-partida-button";
import { formatFechaHora } from "@/lib/utils";
import { useAuthStore } from "@/store/auth-store";

const GENERO_EMOJI: Record<string, string> = {
  fantasía: "🗡️",
  "ciencia ficción": "🚀",
  terror: "🕯️",
};

interface PartidasListProps {
  onReanudar: (codigo: string) => void;
}

export function PartidasList({ onReanudar }: PartidasListProps) {
  const [busqueda, setBusqueda] = useState("");
  // Incluimos el id de usuario en la key para que la lista se refetchee al
  // iniciar o cerrar sesión (anónimo == "0").
  const userId = useAuthStore((s) => s.user?.id ?? "0");
  const { data, isLoading, isError } = useQuery({
    queryKey: ["partidas", userId],
    queryFn: () => api.listarPartidas(),
  });

  const termino = busqueda.trim().toLowerCase();
  const partidasFiltradas = (data ?? []).filter(
    (partida) =>
      termino === "" ||
      partida.nombre_personaje.toLowerCase().includes(termino) ||
      partida.codigo_partida.toLowerCase().includes(termino),
  );

  const tienePartidas = !!data && data.length > 0;

  return (
    <div className="flex flex-col gap-3">
      {tienePartidas && (
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Buscar por código o personaje..."
            className="pl-9"
          />
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-8">
          <Loader message="Cargando partidas..." />
        </div>
      ) : isError ? (
        <p className="text-sm text-destructive py-4 text-center">
          Error al cargar las partidas. Intentá de nuevo.
        </p>
      ) : !tienePartidas ? (
        <p className="text-sm text-muted-foreground py-4 text-center">
          No hay partidas guardadas.
        </p>
      ) : partidasFiltradas.length === 0 ? (
        <p className="text-sm text-muted-foreground py-4 text-center">
          No se encontraron partidas.
        </p>
      ) : (
        <ul className="max-h-[60vh] space-y-3 overflow-y-auto pr-1">
          {partidasFiltradas.map((partida) => (
            <li
              key={partida.codigo_partida}
              className="flex items-center justify-between gap-4 rounded-lg border bg-card p-4"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-base">
                    {GENERO_EMOJI[partida.genero] ?? "📖"}
                  </span>
                  <span className="font-medium truncate">
                    {partida.nombre_personaje}
                  </span>
                  <span
                    className={`shrink-0 items-center justify-center rounded-full px-2 py-0.5 text-center text-xs font-medium ${
                      partida.estado === "en_curso"
                        ? "bg-green-500/15 text-green-700 dark:text-green-400"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {partida.estado === "en_curso" ? "En curso" : "Finalizada"}
                  </span>
                </div>
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <span>
                    {formatFechaHora(
                      partida.actualizada_en ?? partida.creada_en,
                    )}
                  </span>
                  <span>•</span>
                  <span className="font-mono">
                    {partida.codigo_partida.slice(0, 9)}
                  </span>
                  <span>•</span>
                  <span>Turno {partida.turno_actual}</span>
                  <span>•</span>
                  <span title="Versión del contrato de prompts con que se creó">
                    v{partida.prompt_version}
                  </span>
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <EliminarPartidaButton codigo={partida.codigo_partida} />
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onReanudar(partida.codigo_partida)}
                >
                  Reanudar
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
