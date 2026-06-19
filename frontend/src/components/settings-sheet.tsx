"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import {
  type NarrativaFont,
  type NarrativaSize,
  useSettingsStore,
} from "@/store/settings-store";

interface SettingsSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const FONT_OPTIONS: { value: NarrativaFont; label: string }[] = [
  { value: "serif", label: "Serif" },
  { value: "sans", label: "Sans" },
  { value: "dyslexic", label: "Dislexia" },
];

const SIZE_OPTIONS: { value: NarrativaSize; label: string }[] = [
  { value: "sm", label: "Pequeña" },
  { value: "md", label: "Mediana" },
  { value: "lg", label: "Grande" },
];

const THEME_OPTIONS: { value: string; label: string }[] = [
  { value: "light", label: "Claro" },
  { value: "dark", label: "Oscuro" },
  { value: "system", label: "Sistema" },
];

function OptionGroup<T extends string>({
  label,
  value,
  options,
  onSelect,
}: {
  label: string;
  value: T | undefined;
  options: { value: T; label: string }[];
  onSelect: (value: T) => void;
}) {
  return (
    <div className="space-y-2">
      <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="grid grid-cols-3 gap-2">
        {options.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onSelect(opt.value)}
            aria-pressed={value === opt.value}
            className={cn(
              "rounded-md border px-2 py-2 text-sm transition-colors",
              value === opt.value
                ? "border-primary bg-primary/10 text-foreground"
                : "bg-background hover:bg-accent hover:text-accent-foreground",
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function SettingsSheet({ open, onOpenChange }: SettingsSheetProps) {
  const narrativaFont = useSettingsStore((s) => s.narrativaFont);
  const narrativaSize = useSettingsStore((s) => s.narrativaSize);
  const setNarrativaFont = useSettingsStore((s) => s.setNarrativaFont);
  const setNarrativaSize = useSettingsStore((s) => s.setNarrativaSize);

  const { theme, setTheme } = useTheme();
  // El tema solo es legible tras montar en el cliente (evita mismatch de hidratación).
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="left-auto right-0 border-l border-r-0 data-[state=open]:animate-fade-in">
        <SheetHeader>
          <SheetTitle>Ajustes</SheetTitle>
        </SheetHeader>

        <div className="flex-1 space-y-6 overflow-y-auto p-4">
          <OptionGroup
            label="Fuente del narrador"
            value={narrativaFont}
            options={FONT_OPTIONS}
            onSelect={setNarrativaFont}
          />
          <OptionGroup
            label="Tamaño del texto"
            value={narrativaSize}
            options={SIZE_OPTIONS}
            onSelect={setNarrativaSize}
          />
          <OptionGroup
            label="Tema"
            value={mounted ? theme : undefined}
            options={THEME_OPTIONS}
            onSelect={setTheme}
          />

          <p className="narrativa border-t pt-4 text-muted-foreground">
            Así se verá el texto del narrador con estos ajustes.
          </p>
        </div>
      </SheetContent>
    </Sheet>
  );
}
