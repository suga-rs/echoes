/**
 * Estado global de la partida en curso.
 *
 * Persiste solo el código de partida en localStorage; el resto se hidrata
 * llamando a /resume del backend. Esto evita problemas de versiones del
 * estado entre cliente y servidor.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Personaje, Tirada, TurnoHistorial } from "@/lib/types";

/** Estado final que viaja junto al turno cuando la aventura termina. */
interface EstadoFinal {
  estado: "finalizada";
  final: "exito" | "fracaso" | "ambiguo" | null;
  razon: string | null;
}

/** Turno resuelto que llegó por SSE mientras el modal del dado seguía abierto.
 * Se retiene acá (sin tocar el historial) y se vuelca al cerrar el modal. */
interface TurnoPendiente {
  turno: TurnoHistorial;
  imagenPendiente: boolean;
  estadoFinal: EstadoFinal | null;
}

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

  // Streaming
  isStreaming: boolean;
  streamingNarrativa: string | null;
  imagenUltimoTurnoPendiente: boolean;
  // Tirada en curso a animar sobre la página (null = sin overlay de dado).
  tiradaActual: Tirada | null;
  // Turno resuelto retenido mientras el modal del dado está abierto (null = nada
  // pendiente). Se vuelca al historial recién cuando el jugador cierra el modal.
  turnoPendiente: TurnoPendiente | null;

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
  establecerCodigo: (codigo: string) => void;
  resetear: () => void;

  // Streaming actions
  iniciarStreaming: () => void;
  appendStreamToken: (content: string) => void;
  // Si el modal del dado está abierto, retiene el turno (no toca el historial);
  // si no, lo commitea como siempre. `estadoFinal` viaja con el turno.
  finalizarStreaming: (
    turno: TurnoHistorial,
    imagenPendiente: boolean,
    estadoFinal?: EstadoFinal | null,
  ) => void;
  cancelarStreaming: () => void;
  actualizarImagenTurno: (turnoNum: number, url: string) => void;
  // Tirada: abre el overlay y descarta la narrativa de preparación (fase 1),
  // que será reemplazada por el desenlace (fase 2) que se streamea a continuación.
  iniciarTirada: (tirada: Tirada) => void;
  cerrarTirada: () => void;
  // Vuelca el turno retenido al historial (lo invoca el replay tras cerrar el modal).
  commitTurnoPendiente: () => void;
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
      isStreaming: false,
      streamingNarrativa: null,
      imagenUltimoTurnoPendiente: false,
      tiradaActual: null,
      turnoPendiente: null,

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

      establecerCodigo: (codigo) => set({ codigoPartida: codigo }),

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
          isStreaming: false,
          streamingNarrativa: null,
          imagenUltimoTurnoPendiente: false,
          tiradaActual: null,
          turnoPendiente: null,
        }),

      iniciarStreaming: () => set({ isStreaming: true, streamingNarrativa: "" }),

      appendStreamToken: (content) =>
        set((state) => ({ streamingNarrativa: (state.streamingNarrativa ?? "") + content })),

      finalizarStreaming: (turno, imagenPendiente, estadoFinal = null) =>
        set((state) => {
          // Siempre retenemos el turno: la narrativa se revela con typewriter, no
          // se commitea de golpe. Con el modal del dado abierto, el revelado espera
          // al cierre (ver cerrarTirada); si no, arranca de inmediato.
          const turnoPendiente = { turno, imagenPendiente, estadoFinal };
          if (state.tiradaActual !== null) {
            return { turnoPendiente };
          }
          return { turnoPendiente, isStreaming: true, streamingNarrativa: "" };
        }),

      cancelarStreaming: () => set({
        isStreaming: false,
        streamingNarrativa: null,
        imagenUltimoTurnoPendiente: false,
        tiradaActual: null,
        turnoPendiente: null,
      }),

      iniciarTirada: (tirada) =>
        // Al tirar, descartamos la narrativa de preparación (fase 1): el
        // desenlace (fase 2) se streamea limpio a continuación.
        set({ tiradaActual: tirada, streamingNarrativa: "" }),

      cerrarTirada: () =>
        set((state) => {
          // Cierre temprano (el desenlace aún no llegó): dejamos la narrativa en
          // vivo; el StreamingTurnoCard reaparece y onTurno commiteará normal.
          if (!state.turnoPendiente) {
            return { tiradaActual: null };
          }
          // Desenlace ya bufferizado: arrancamos el replay typewriter desde cero;
          // un efecto en la página re-tipea y luego llama commitTurnoPendiente.
          return { tiradaActual: null, isStreaming: true, streamingNarrativa: "" };
        }),

      commitTurnoPendiente: () =>
        set((state) => {
          const tp = state.turnoPendiente;
          if (!tp) return {};
          return {
            historial: [...state.historial, tp.turno],
            isStreaming: false,
            streamingNarrativa: null,
            imagenUltimoTurnoPendiente: tp.imagenPendiente,
            turnoPendiente: null,
            ...(tp.estadoFinal
              ? { estado: tp.estadoFinal.estado, final: tp.estadoFinal.final, razonFin: tp.estadoFinal.razon }
              : {}),
          };
        }),

      actualizarImagenTurno: (turnoNum, url) =>
        set((state) => {
          // La imagen puede llegar mientras el turno sigue retenido (turno final
          // con tirada): la guardamos en el turno pendiente, no en el historial.
          if (state.turnoPendiente && state.turnoPendiente.turno.turno === turnoNum) {
            return {
              turnoPendiente: {
                ...state.turnoPendiente,
                imagenPendiente: false,
                turno: { ...state.turnoPendiente.turno, imagen_url: url },
              },
            };
          }
          return {
            imagenUltimoTurnoPendiente: false,
            historial: state.historial.map((t) =>
              t.turno === turnoNum ? { ...t, imagen_url: url } : t,
            ),
          };
        }),
    }),
    {
      name: "aventuras-partida",
      // Solo persistimos el código. El resto se hidrata desde el backend.
      partialize: (state) => ({ codigoPartida: state.codigoPartida }),
    },
  ),
);
