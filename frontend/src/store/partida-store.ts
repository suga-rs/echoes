/**
 * Estado global de la partida en curso.
 *
 * Persiste solo el código de partida en localStorage; el resto se hidrata
 * llamando a /resume del backend. Esto evita problemas de versiones del
 * estado entre cliente y servidor.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Personaje, TurnoHistorial } from "@/lib/types";

interface PartidaState {
  codigoPartida: string | null;
  personaje: Personaje | null;
  objetivo: string | null;
  inventario: string[];
  ubicacion: string | null;
  historial: TurnoHistorial[];
  estado: "en_curso" | "finalizada" | null;
  final: "exito" | "fracaso" | "ambiguo" | null;
  razonFin: string | null;

  // Acciones
  iniciarPartida: (data: {
    codigo: string;
    personaje: Personaje;
    objetivo: string;
    primerTurno: TurnoHistorial;
  }) => void;
  agregarTurno: (turno: TurnoHistorial) => void;
  actualizarEstadoFinal: (
    estado: "en_curso" | "finalizada",
    final: "exito" | "fracaso" | "ambiguo" | null,
    razon: string | null,
  ) => void;
  hidratarDesdeBackend: (data: {
    codigo: string;
    personaje: Personaje;
    objetivo: string;
    ubicacion: string;
    inventario: string[];
    historial: TurnoHistorial[];
    estado: "en_curso" | "finalizada";
    final: "exito" | "fracaso" | "ambiguo" | null;
    razonFin: string | null;
  }) => void;
  setInventarioYUbicacion: (inventario: string[], ubicacion: string) => void;
  resetear: () => void;
}

export const usePartidaStore = create<PartidaState>()(
  persist(
    (set) => ({
      codigoPartida: null,
      personaje: null,
      objetivo: null,
      inventario: [],
      ubicacion: null,
      historial: [],
      estado: null,
      final: null,
      razonFin: null,

      iniciarPartida: ({ codigo, personaje, objetivo, primerTurno }) =>
        set({
          codigoPartida: codigo,
          personaje,
          objetivo,
          inventario: personaje.inventario,
          ubicacion: null,
          historial: [primerTurno],
          estado: "en_curso",
          final: null,
          razonFin: null,
        }),

      agregarTurno: (turno) =>
        set((state) => ({ historial: [...state.historial, turno] })),

      actualizarEstadoFinal: (estado, final, razon) =>
        set({ estado, final, razonFin: razon }),

      hidratarDesdeBackend: ({
        codigo,
        personaje,
        objetivo,
        ubicacion,
        inventario,
        historial,
        estado,
        final,
        razonFin,
      }) =>
        set({
          codigoPartida: codigo,
          personaje,
          objetivo,
          ubicacion,
          inventario,
          historial,
          estado,
          final,
          razonFin,
        }),

      setInventarioYUbicacion: (inventario, ubicacion) =>
        set({ inventario, ubicacion }),

      resetear: () =>
        set({
          codigoPartida: null,
          personaje: null,
          objetivo: null,
          inventario: [],
          ubicacion: null,
          historial: [],
          estado: null,
          final: null,
          razonFin: null,
        }),
    }),
    {
      name: "aventuras-partida",
      // Solo persistimos el código. El resto se hidrata desde el backend.
      partialize: (state) => ({ codigoPartida: state.codigoPartida }),
    },
  ),
);
