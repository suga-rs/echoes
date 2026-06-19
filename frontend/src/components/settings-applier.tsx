"use client";

import { useEffect } from "react";
import {
  FONT_STACKS,
  SIZE_VALUES,
  useSettingsStore,
} from "@/store/settings-store";

/**
 * Aplica las preferencias de lectura como variables CSS sobre `<html>`.
 * Corre tras la hidratación; el flash inicial lo evita el script pre-paint
 * del layout. No renderiza nada.
 */
export function SettingsApplier() {
  const narrativaFont = useSettingsStore((s) => s.narrativaFont);
  const narrativaSize = useSettingsStore((s) => s.narrativaSize);

  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty("--font-narrativa", FONT_STACKS[narrativaFont]);
    root.style.setProperty("--narrativa-size", SIZE_VALUES[narrativaSize]);
  }, [narrativaFont, narrativaSize]);

  return null;
}
