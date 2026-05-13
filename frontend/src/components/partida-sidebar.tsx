"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Loader } from "@/components/ui/loader";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

const GENERO_EMOJI: Record<string, string> = {
  "fantasía": "🗡️",
  "ciencia ficción": "🚀",
  "terror": "🕯️",
};

interface PartidaSidebarProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onReanudar: (codigo: string) => void;
  codigoActivo: string | null;
}

export function PartidaSidebar({
  open,
  onOpenChange,
  onReanudar,
  codigoActivo,
}: PartidaSidebarProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["partidas"],
    queryFn: () => api.listarPartidas(),
  });

  const handleReanudar = (codigo: string) => {
    onReanudar(codigo);
    onOpenChange(false);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>Partidas</SheetTitle>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto p-4">
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader message="Cargando..." />
            </div>
          ) : isError ? (
            <p className="text-sm text-destructive text-center py-4">
              Error al cargar las partidas.
            </p>
          ) : !data || data.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No hay partidas guardadas.
            </p>
          ) : (
            <ul className="space-y-2">
              {data.map((partida) => {
                const esActiva = partida.codigo_partida === codigoActivo;
                return (
                  <li
                    key={partida.codigo_partida}
                    className={cn(
                      "rounded-lg border p-3",
                      esActiva
                        ? "bg-primary/10 border-l-2 border-l-primary"
                        : "bg-card"
                    )}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span>{GENERO_EMOJI[partida.genero] ?? "📖"}</span>
                      <span className="font-medium text-sm truncate flex-1">
                        {partida.nombre_personaje}
                      </span>
                      <span
                        className={cn(
                          "shrink-0 rounded-full px-2 py-0.5 text-xs font-medium",
                          partida.estado === "en_curso"
                            ? "bg-green-500/15 text-green-700 dark:text-green-400"
                            : "bg-muted text-muted-foreground"
                        )}
                      >
                        {partida.estado === "en_curso" ? "En curso" : "Finalizada"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-xs text-muted-foreground">
                        <span>Turno {partida.turno_actual}</span>
                        <span className="font-mono ml-2">
                          {partida.codigo_partida.slice(0, 9)}
                        </span>
                      </div>
                      {!esActiva && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 text-xs"
                          onClick={() => handleReanudar(partida.codigo_partida)}
                        >
                          Reanudar
                        </Button>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
