/**
 * Tipos del dominio. Espejan los DTOs del backend.
 * Cuando el backend cambie, regenerar con `pnpm gen:types` y actualizar.
 */

export type Genero = "fantasía" | "ciencia ficción" | "terror";

export type EstadoPartida = "en_curso" | "finalizada";

export type TipoFinal = "exito" | "fracaso" | "ambiguo";

export type Habilidad =
  | "fuerza"
  | "destreza"
  | "constitucion"
  | "inteligencia"
  | "sabiduria"
  | "carisma";

export type Banda = "trivial" | "facil" | "media" | "dificil" | "heroica";

export type ResultadoTirada =
  | "exito_critico"
  | "exito"
  | "fracaso"
  | "fracaso_critico";

export interface Atributos {
  fuerza: number;
  destreza: number;
  constitucion: number;
  inteligencia: number;
  sabiduria: number;
  carisma: number;
}

export interface Tirada {
  habilidad: Habilidad;
  banda: Banda;
  dc: number;
  d20: number;
  modificador: number;
  total: number;
  resultado: ResultadoTirada;
}

export type EfectoCondicion = "desventaja" | "dano_por_turno";

export interface Condicion {
  tipo: string;
  efecto: EfectoCondicion;
  // Entero de turnos restantes, o "hasta_curar" / "hasta_evento".
  duracion: number | string;
}

export interface Personaje {
  nombre: string;
  descripcion_narrativa: string;
  descripcion_visual_en: string;
  inventario: string[];
  // Partidas previas al sistema de tiradas no traen atributos.
  atributos?: Atributos;
  // Puntos de vida y condiciones (Hito 2). Partidas previas deserializan a tope.
  pv_actual?: number;
  pv_max?: number;
  condiciones?: Condicion[];
}

export interface TurnoResponse {
  turno: number;
  narrativa: string;
  opciones: string[];
  imagen_url: string | null;
  estado: EstadoPartida;
  final: TipoFinal | null;
  razon_fin: string | null;
  tirada?: Tirada | null;
  pv_actual?: number;
  pv_max?: number;
  condiciones?: Condicion[];
  dano_recibido?: number;
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
  pv_actual?: number;
  pv_max?: number;
  condiciones?: Condicion[];
}

export interface TurnoHistorial {
  turno: number;
  accion_jugador: string;
  narrativa: string;
  opciones: string[];
  imagen_url: string | null;
  feedback?: string | null;
  tirada?: Tirada | null;
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

export interface PartidaResumen {
  codigo_partida: string;
  nombre_personaje: string;
  turno_actual: number;
  estado: EstadoPartida;
  genero: Genero;
  creada_en: string;
  actualizada_en?: string | null;
  prompt_version: string;
}

export interface RandomDescriptionResponse {
  descripcion: string;
}

export interface UsuarioPublico {
  id: string;
  username: string;
  creada_en: string;
  avatar_url: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UsuarioPublico;
}

export interface PerfilResponse {
  user: UsuarioPublico;
  partidas: PartidaResumen[];
}

export interface AvatarResponse {
  avatar_url: string;
}
