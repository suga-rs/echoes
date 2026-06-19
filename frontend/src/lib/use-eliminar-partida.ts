/**
 * Hook compartido para eliminar una partida.
 *
 * Invalida la lista de partidas tras el borrado y, si se eliminó la partida
 * activa, resetea el estado local del juego. Usado por la lista y el sidebar.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { usePartidaStore } from "@/store/partida-store";

export function useEliminarPartida() {
  const queryClient = useQueryClient();
  const codigoActivo = usePartidaStore((s) => s.codigoPartida);
  const resetear = usePartidaStore((s) => s.resetear);

  return useMutation({
    mutationFn: (codigo: string) => api.eliminarPartida(codigo),
    onSuccess: (_data, codigo) => {
      queryClient.invalidateQueries({ queryKey: ["partidas"] });
      if (codigo === codigoActivo) resetear();
    },
  });
}
