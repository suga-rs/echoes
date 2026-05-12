"use client";

import { useState } from "react";
import { Copy, Plus, Package } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { usePartidaStore } from "@/store/partida-store";
import { ThemeToggle } from "./theme-toggle";

interface HeaderProps {
  onNuevaPartida: () => void;
}

export function Header({ onNuevaPartida }: HeaderProps) {
  const [showInventario, setShowInventario] = useState(false);
  const [copiado, setCopiado] = useState(false);
  const codigo = usePartidaStore((s) => s.codigoPartida);
  const objetivo = usePartidaStore((s) => s.objetivo);
  const personaje = usePartidaStore((s) => s.personaje);
  const inventario = usePartidaStore((s) => s.inventario);

  const copiarCodigo = async () => {
    if (!codigo) return;
    await navigator.clipboard.writeText(codigo);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 1500);
  };

  return (
    <header className="sticky top-0 z-30 bg-background/95 backdrop-blur border-b">
      <div className="max-w-3xl mx-auto px-4 py-3 flex items-center gap-3">
        <div className="flex-1 min-w-0">
          {objetivo ? (
            <>
              <div className="text-xs text-muted-foreground uppercase tracking-wide">
                Objetivo
              </div>
              <div className="text-sm font-medium truncate">{objetivo}</div>
            </>
          ) : (
            <div className="text-sm font-semibold">Echoes</div>
          )}
        </div>

        {codigo && (
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowInventario(true)}
              title="Ver inventario"
            >
              <Package className="h-4 w-4" />
              <span className="ml-1 text-xs">{inventario.length}</span>
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={copiarCodigo}
              title="Copiar código de partida"
              className="text-xs font-mono"
            >
              <Copy className="h-3 w-3 mr-1" />
              {copiado ? "¡copiado!" : codigo.slice(0, 9)}
            </Button>
          </>
        )}

        <ThemeToggle />

        <Button size="sm" onClick={onNuevaPartida} title="Nueva aventura">
          <Plus className="h-4 w-4 mr-1" />
          Nueva
        </Button>
      </div>

      <Dialog open={showInventario} onOpenChange={setShowInventario}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Inventario de {personaje?.nombre}</DialogTitle>
            <DialogDescription>
              {personaje?.descripcion_narrativa}
            </DialogDescription>
          </DialogHeader>
          {inventario.length === 0 ? (
            <p className="text-muted-foreground italic text-sm">
              No tenés objetos en tu inventario.
            </p>
          ) : (
            <ul className="grid gap-2">
              {inventario.map((item, idx) => (
                <li
                  key={idx}
                  className="flex items-center gap-2 p-2 bg-muted rounded-md text-sm"
                >
                  <span className="text-muted-foreground">•</span>
                  {item}
                </li>
              ))}
            </ul>
          )}
        </DialogContent>
      </Dialog>
    </header>
  );
}
