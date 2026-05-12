/**
 * Tipos del dominio. Espejan los DTOs del backend.
 * Cuando el backend cambie, regenerar con `npm run gen:types` y actualizar.
 */

export type Genero = "fantasía" | "ciencia ficción" | "terror";

export type EstadoPartida = "en_curso" | "finalizada";

export type TipoFinal = "exito" | "fracaso" | "ambiguo";

export interface Personaje {
  nombre: string;
  descripcion_narrativa: string;
  descripcion_visual_en: string;
  inventario: string[];
}

export interface TurnoResponse {
  turno: number;
  narrativa: string;
  opciones: string[];
  imagen_url: string | null;
  estado: EstadoPartida;
  final: TipoFinal | null;
  razon_fin: string | null;
}

export interface StartResponse {
  codigo_partida: string;
  personaje: Personaje;
  objetivo: string;
  primer_turno: TurnoResponse;
}

export interface StateResponse {
  codigo_partida: string;
  turno_actual: number;
  estado: EstadoPartida;
  personaje_nombre: string;
  inventario: string[];
  ubicacion: string;
  objetivo: string;
  eventos_clave: string[];
  npcs_conocidos: string[];
}

export interface TurnoHistorial {
  turno: number;
  accion_jugador: string;
  narrativa: string;
  opciones: string[];
  imagen_url: string | null;
}

export interface Partida {
  id: string;
  codigo_partida: string;
  metadata: {
    genero: Genero;
    creada_en: string;
    turno_actual: number;
    estado: EstadoPartida;
    final: TipoFinal | null;
    razon_fin: string | null;
    imagenes_generadas: number;
  };
  personaje: Personaje;
  world_state: {
    ubicacion_actual: string;
    objetivo: string;
    eventos_clave: string[];
    npcs: Array<{ nombre: string; descripcion: string; actitud: string }>;
    pistas: string[];
  };
  historial: TurnoHistorial[];
}

export interface ApiError {
  code: string;
  mensaje: string;
  detalles: Record<string, unknown>;
}
