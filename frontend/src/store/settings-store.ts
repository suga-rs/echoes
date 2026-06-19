/**
 * Preferencias de lectura del narrador (fuente y tamaño).
 *
 * Persiste en localStorage para sobrevivir recargas. Un applier escribe estos
 * valores como variables CSS (`--font-narrativa`, `--narrativa-size`) sobre
 * `<html>`, y `.narrativa` las consume. El tema lo sigue manejando next-themes.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type NarrativaFont = "serif" | "sans" | "dyslexic";
export type NarrativaSize = "sm" | "md" | "lg";

/** Mapa enum → stack de fuentes concreto (fuente única de verdad). */
export const FONT_STACKS: Record<NarrativaFont, string> = {
  serif: '"Crimson Text", Georgia, serif',
  sans: "Inter, system-ui, sans-serif",
  dyslexic: '"Atkinson Hyperlegible", "Comic Sans MS", sans-serif',
};

/** Mapa enum → tamaño en rem. `md` coincide con el baseline previo (1.05rem). */
export const SIZE_VALUES: Record<NarrativaSize, string> = {
  sm: "0.95rem",
  md: "1.05rem",
  lg: "1.2rem",
};

export const SETTINGS_STORAGE_KEY = "aventuras-settings";

interface SettingsState {
  narrativaFont: NarrativaFont;
  narrativaSize: NarrativaSize;
  setNarrativaFont: (font: NarrativaFont) => void;
  setNarrativaSize: (size: NarrativaSize) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      narrativaFont: "serif",
      narrativaSize: "md",
      setNarrativaFont: (narrativaFont) => set({ narrativaFont }),
      setNarrativaSize: (narrativaSize) => set({ narrativaSize }),
    }),
    { name: SETTINGS_STORAGE_KEY },
  ),
);
