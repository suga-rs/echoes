/**
 * Cliente HTTP del backend. Una función por endpoint, sin clases.
 *
 * Todas las funciones lanzan `ApiClientError` con detalle estructurado
 * si la respuesta no es 2xx, para que React Query las maneje uniformemente.
 */

import type {
  ApiError,
  AuthResponse,
  AvatarResponse,
  EstadoPartida,
  Partida,
  PartidaResumen,
  PerfilResponse,
  RandomDescriptionResponse,
  StartResponse,
  StateResponse,
  TipoFinal,
  TurnoResponse,
  Genero,
} from "./types";
import { getAuthToken } from "@/store/auth-store";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

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
      ...authHeaders(),
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
  // 204 No Content (p. ej. DELETE) no trae cuerpo que parsear.
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export interface TurnoStreamData {
  turno: number;
  narrativa: string;
  opciones: string[];
  estado: EstadoPartida;
  final: TipoFinal | null;
  razon_fin: string | null;
  imagen_pendiente: boolean;
}

export interface TurnoStreamHandlers {
  onToken: (content: string) => void;
  onTurno: (data: TurnoStreamData) => void;
  onImagen: (url: string) => void;
  onError: (err: ApiClientError) => void;
  onDone: () => void;
}

export async function avanzarTurnoStream(
  codigo: string,
  accion: string,
  handlers: TurnoStreamHandlers,
): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/partidas/${codigo}/turn/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ accion }),
  });

  if (!res.ok || !res.body) {
    let detail: ApiError | null = null;
    try {
      detail = await res.json();
    } catch { /* ignore */ }
    handlers.onError(new ApiClientError(
      res.status,
      detail?.code ?? "http_error",
      detail?.mensaje ?? `HTTP ${res.status}`,
      detail?.detalles ?? {},
    ));
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let currentEvent = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });

      const lines = buf.split("\n");
      buf = lines.pop() ?? "";

      for (const line of lines) {
        if (line.startsWith("event: ")) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          const raw = line.slice(6).trim();
          try {
            const data = JSON.parse(raw);
            if (currentEvent === "token") {
              handlers.onToken(data.content as string);
            } else if (currentEvent === "turno") {
              handlers.onTurno(data as TurnoStreamData);
            } else if (currentEvent === "imagen") {
              handlers.onImagen(data.imagen_url as string);
            } else if (currentEvent === "error") {
              handlers.onError(new ApiClientError(500, data.code, data.mensaje));
            } else if (currentEvent === "done") {
              handlers.onDone();
            }
          } catch { /* malformed data line, skip */ }
          currentEvent = "";
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export const api = {
  iniciarPartida: (
    genero: Genero,
    descripcion_personaje: string,
    premisa?: string | null,
    tono?: string | null,
  ) =>
    request<StartResponse>("/api/partidas/start", {
      method: "POST",
      body: JSON.stringify({
        genero,
        descripcion_personaje,
        premisa: premisa || null,
        tono: tono || null,
      }),
    }),

  avanzarTurno: (codigo: string, accion: string) =>
    request<TurnoResponse>(`/api/partidas/${codigo}/turn`, {
      method: "POST",
      body: JSON.stringify({ accion }),
    }),

  generarImagenTurno: (codigo: string, turno: number) =>
    request<{ imagen_url: string }>(`/api/partidas/${codigo}/turn/${turno}/image`, {
      method: "POST",
    }),

  marcarFeedback: (codigo: string, turno: number, incoherente = true) =>
    request<{ feedback: string | null }>(`/api/partidas/${codigo}/turn/${turno}/feedback`, {
      method: "POST",
      body: JSON.stringify({ incoherente }),
    }),

  reanudarPartida: (codigo: string) =>
    request<Partida>(`/api/partidas/${codigo}/resume`),

  getEstado: (codigo: string) =>
    request<StateResponse>(`/api/partidas/${codigo}/state`),

  listarPartidas: () =>
    request<PartidaResumen[]>("/api/partidas"),

  eliminarPartida: (codigo: string) =>
    request<void>(`/api/partidas/${codigo}`, { method: "DELETE" }),

  generarDescripcionAleatoria: (genero: Genero) =>
    request<RandomDescriptionResponse>("/api/partidas/random-description", {
      method: "POST",
      body: JSON.stringify({ genero }),
    }),

  register: (username: string, password: string) =>
    request<AuthResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  login: (username: string, password: string) =>
    request<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  getPerfil: () => request<PerfilResponse>("/api/usuarios/me"),

  uploadAvatar: async (file: File): Promise<AvatarResponse> => {
    const form = new FormData();
    form.append("file", file);
    // No fijamos Content-Type: el navegador agrega el boundary del multipart.
    const res = await fetch(`${BASE_URL}/api/usuarios/me/avatar`, {
      method: "POST",
      headers: { ...authHeaders() },
      body: form,
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
    return res.json() as Promise<AvatarResponse>;
  },
};
