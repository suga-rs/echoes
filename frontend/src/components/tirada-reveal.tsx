import type { Banda, Habilidad, ResultadoTirada, Tirada } from "@/lib/types";

const HABILIDAD_LABEL: Record<Habilidad, string> = {
  fuerza: "Fuerza",
  destreza: "Destreza",
  constitucion: "Constitución",
  inteligencia: "Inteligencia",
  sabiduria: "Sabiduría",
  carisma: "Carisma",
};

const BANDA_LABEL: Record<Banda, string> = {
  trivial: "Trivial",
  facil: "Fácil",
  media: "Media",
  dificil: "Difícil",
  heroica: "Heroica",
};

const RESULTADO_LABEL: Record<ResultadoTirada, string> = {
  exito_critico: "¡Éxito crítico!",
  exito: "Éxito",
  fracaso: "Fracaso",
  fracaso_critico: "Fracaso crítico",
};

const RESULTADO_CLASS: Record<ResultadoTirada, string> = {
  exito_critico: "text-amber-500 border-amber-500/40 bg-amber-500/10",
  exito: "text-emerald-500 border-emerald-500/40 bg-emerald-500/10",
  fracaso: "text-muted-foreground border-border bg-muted/40",
  fracaso_critico: "text-destructive border-destructive/40 bg-destructive/10",
};

function signo(n: number): string {
  return n >= 0 ? `+${n}` : `${n}`;
}

/**
 * Revelado estático de una tirada resuelta. Es la fuente de verdad textual y el
 * fallback de reduced-motion; la animación 3D es solo realce sobre estos valores.
 */
export function TiradaReveal({ tirada }: { tirada: Tirada }) {
  return (
    <div
      className={`mb-3 rounded-md border px-3 py-2 text-sm ${RESULTADO_CLASS[tirada.resultado]}`}
      role="status"
      aria-label={`Tirada de ${HABILIDAD_LABEL[tirada.habilidad]}: ${RESULTADO_LABEL[tirada.resultado]}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium">
          Tirada de {HABILIDAD_LABEL[tirada.habilidad]} · {BANDA_LABEL[tirada.banda]} (DC {tirada.dc})
        </span>
        <span className="font-semibold uppercase tracking-wide text-xs">
          {RESULTADO_LABEL[tirada.resultado]}
        </span>
      </div>
      <div className="mt-1 font-mono text-xs text-foreground/80">
        d20 {tirada.d20} {signo(tirada.modificador)} = {tirada.total} vs DC {tirada.dc}
      </div>
    </div>
  );
}
