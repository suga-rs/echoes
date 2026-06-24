import type { Condicion } from "@/lib/types";

const ETIQUETA_CONDICION: Record<string, string> = {
  envenenado: "Envenenado",
  sangrando: "Sangrando",
  aturdido: "Aturdido",
  exhausto: "Exhausto",
};

function duracionLegible(duracion: number | string): string {
  if (typeof duracion === "number") return `${duracion} turno${duracion === 1 ? "" : "s"}`;
  if (duracion === "hasta_curar") return "hasta curarse";
  if (duracion === "hasta_evento") return "hasta un evento";
  return String(duracion);
}

/** Barra de vida (pv_actual/pv_max) con badges de condiciones activas. Resalta
 * el daño recibido este turno. Verde→amarillo→rojo según la fracción de vida. */
export function BarraVida({
  pvActual,
  pvMax,
  condiciones,
  danoUltimoTurno = 0,
}: {
  pvActual: number;
  pvMax: number;
  condiciones: Condicion[];
  danoUltimoTurno?: number;
}) {
  const fraccion = pvMax > 0 ? Math.max(0, Math.min(1, pvActual / pvMax)) : 0;
  const color =
    fraccion > 0.5 ? "bg-emerald-500" : fraccion > 0.25 ? "bg-amber-500" : "bg-red-600";

  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-muted-foreground">Vida</span>
        <span className="font-mono text-xs">
          {pvActual}/{pvMax}
          {danoUltimoTurno > 0 && (
            <span className="ml-2 font-semibold text-red-600">−{danoUltimoTurno}</span>
          )}
        </span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${fraccion * 100}%` }}
          role="progressbar"
          aria-valuenow={pvActual}
          aria-valuemin={0}
          aria-valuemax={pvMax}
        />
      </div>
      {condiciones.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {condiciones.map((c, idx) => (
            <span
              key={`${c.tipo}-${idx}`}
              title={`${c.efecto === "desventaja" ? "Desventaja en las tiradas" : "Pierde vida cada turno"} · ${duracionLegible(c.duracion)}`}
              className="rounded-full border border-red-500/40 bg-red-500/10 px-2 py-0.5 text-[11px] font-medium text-red-700 dark:text-red-300"
            >
              {ETIQUETA_CONDICION[c.tipo] ?? c.tipo}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
