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
export type DiceScheme = "marfil" | "obsidiana" | "esmeralda";

/** Mapa enum → stack de fuentes concreto (fuente única de verdad). */
export const FONT_STACKS: Record<NarrativaFont, string> = {
  serif: '"Crimson Text", Georgia, serif',
  sans: '"Atkinson Hyperlegible",Inter, system-ui, sans-serif',
  dyslexic: '"Lexend Deca", "Comic Sans MS", sans-serif',
};

/** Mapa enum → tamaño en rem. `md` coincide con el baseline previo (1.05rem). */
export const SIZE_VALUES: Record<NarrativaSize, string> = {
  sm: "0.95rem",
  md: "1.05rem",
  lg: "1.2rem",
};

/**
 * Mapa enum → paleta concreta del d20 (fuente única de verdad). El brillo emisivo
 * por resultado (oro/esmeralda/gris/rojo) es semántico y NO lo define el esquema.
 * `body` es un hex numérico (lo consume three.js); `label` es un color CSS (es el
 * `fillStyle` del canvas que rotula las caras).
 */
export const DICE_SCHEMES: Record<
  DiceScheme,
  { body: number; label: string; metalness: number; roughness: number }
> = {
  marfil: { body: 0xb22222, label: "#D44646", metalness: 0.75, roughness: 0.7 }, //Carmesí
  obsidiana: {
    body: 0x0f52ba,
    label: "#5C76AF",
    metalness: 0.75,
    roughness: 0.7,
  }, // Zafiro
  esmeralda: {
    body: 0x50c878,
    label: "#D8F5DD",
    metalness: 0.75,
    roughness: 0.7,
  }, // Esmeralda
};

export const SETTINGS_STORAGE_KEY = "aventuras-settings";

interface SettingsState {
  narrativaFont: NarrativaFont;
  narrativaSize: NarrativaSize;
  diceScheme: DiceScheme;
  setNarrativaFont: (font: NarrativaFont) => void;
  setNarrativaSize: (size: NarrativaSize) => void;
  setDiceScheme: (scheme: DiceScheme) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      narrativaFont: "serif",
      narrativaSize: "md",
      diceScheme: "marfil",
      setNarrativaFont: (narrativaFont) => set({ narrativaFont }),
      setNarrativaSize: (narrativaSize) => set({ narrativaSize }),
      setDiceScheme: (diceScheme) => set({ diceScheme }),
    }),
    { name: SETTINGS_STORAGE_KEY },
  ),
);
