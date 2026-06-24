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

/**
 * Revelado de una tirada resuelta para el jugador. Muestra la habilidad puesta a
 * prueba, su dificultad y el desenlace; los números técnicos (d20, modificador,
 * total, DC) se omiten para no confundir a un jugador no técnico.
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
          Prueba de {HABILIDAD_LABEL[tirada.habilidad]} · {BANDA_LABEL[tirada.banda]}
        </span>
        <span className="font-semibold uppercase tracking-wide text-xs">
          {RESULTADO_LABEL[tirada.resultado]}
        </span>
      </div>
    </div>
  );
}
