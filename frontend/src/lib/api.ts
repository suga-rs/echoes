/**
 * Cliente HTTP del backend. Una función por endpoint, sin clases.
 *
 * Todas las funciones lanzan `ApiClientError` con detalle estructurado
 * si la respuesta no es 2xx, para que React Query las maneje uniformemente.
 */

import type {
  ApiError,
  Partida,
  StartResponse,
  StateResponse,
  TurnoResponse,
  Genero,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiClientError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public detalles: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });

  if (!res.ok) {
    let detail: ApiError | null = null;
    try {
      detail = await res.json();
    } catch {
      // ignore
    }
    throw new ApiClientError(
      res.status,
      detail?.code || "http_error",
      detail?.mensaje || `HTTP ${res.status}`,
      detail?.detalles || {},
    );
  }
  return res.json() as Promise<T>;
}

export const api = {
  iniciarPartida: (genero: Genero, descripcion_personaje: string) =>
    request<StartResponse>("/api/partidas/start", {
      method: "POST",
      body: JSON.stringify({ genero, descripcion_personaje }),
    }),

  avanzarTurno: (codigo: string, accion: string) =>
    request<TurnoResponse>(`/api/partidas/${codigo}/turn`, {
      method: "POST",
      body: JSON.stringify({ accion }),
    }),

  reanudarPartida: (codigo: string) =>
    request<Partida>(`/api/partidas/${codigo}/resume`),

  getEstado: (codigo: string) =>
    request<StateResponse>(`/api/partidas/${codigo}/state`),
};
