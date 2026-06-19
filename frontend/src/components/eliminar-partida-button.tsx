"use client";

import { useState } from "react";
import { Check, Trash2, X } from "lucide-react";
import { useEliminarPartida } from "@/lib/use-eliminar-partida";
import { useAuthStore } from "@/store/auth-store";

interface EliminarPartidaButtonProps {
  codigo: string;
}

/**
 * Control de borrado de una partida con confirmación inline. Solo se renderiza
 * para usuarios autenticados (las partidas anónimas viven en el bucket
 * compartido "Creator" y no se pueden borrar).
 */
export function EliminarPartidaButton({ codigo }: EliminarPartidaButtonProps) {
  const user = useAuthStore((s) => s.user);
  const [confirmando, setConfirmando] = useState(false);
  const { mutate, isPending } = useEliminarPartida();

  if (!user) return null;

  if (confirmando) {
    return (
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => mutate(codigo)}
          disabled={isPending}
          aria-label="Confirmar eliminación"
          title="Confirmar eliminación"
          className="text-destructive hover:opacity-80 disabled:opacity-50"
        >
          <Check className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={() => setConfirmando(false)}
          disabled={isPending}
          aria-label="Cancelar eliminación"
          title="Cancelar"
          className="text-muted-foreground hover:opacity-80 disabled:opacity-50"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => setConfirmando(true)}
      aria-label="Eliminar partida"
      title="Eliminar partida"
      className="text-muted-foreground hover:text-destructive"
    >
      <Trash2 className="h-4 w-4" />
    </button>
  );
}
