import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const FECHA_HORA_FORMATTER = new Intl.DateTimeFormat("es-AR", {
  dateStyle: "short",
  timeStyle: "short",
  hour12: false,
});

/** Formatea una fecha ISO a "9 jun 2026, 14:30" (es-AR). */
export function formatFechaHora(iso: string): string {
  return FECHA_HORA_FORMATTER.format(new Date(iso));
}
