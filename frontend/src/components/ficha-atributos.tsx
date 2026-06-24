import type { Atributos } from "@/lib/types";

const ORDEN: Array<{ key: keyof Atributos; label: string; abbr: string }> = [
  { key: "fuerza", label: "Fuerza", abbr: "FUE" },
  { key: "destreza", label: "Destreza", abbr: "DES" },
  { key: "constitucion", label: "Constitución", abbr: "CON" },
  { key: "inteligencia", label: "Inteligencia", abbr: "INT" },
  { key: "sabiduria", label: "Sabiduría", abbr: "SAB" },
  { key: "carisma", label: "Carisma", abbr: "CAR" },
];

function modificador(score: number): string {
  const mod = Math.floor((score - 10) / 2);
  return mod >= 0 ? `+${mod}` : `${mod}`;
}

/** Bloque de los seis atributos con su modificador derivado. */
export function FichaAtributos({ atributos }: { atributos: Atributos }) {
  return (
    <div className="grid grid-cols-3 gap-2">
      {ORDEN.map(({ key, label, abbr }) => (
        <div
          key={key}
          className="flex flex-col items-center rounded-md border bg-muted/40 p-2"
          title={label}
        >
          <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
            {abbr}
          </span>
          <span className="text-lg font-semibold leading-none">{atributos[key]}</span>
          <span className="font-mono text-xs text-muted-foreground">
            {modificador(atributos[key])}
          </span>
        </div>
      ))}
    </div>
  );
}
