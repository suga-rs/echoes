import { act, render } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { SettingsApplier } from "@/components/settings-applier";
import {
  FONT_STACKS,
  SIZE_VALUES,
  useSettingsStore,
} from "@/store/settings-store";

beforeEach(() => {
  useSettingsStore.setState({ narrativaFont: "serif", narrativaSize: "md" });
  document.documentElement.style.removeProperty("--font-narrativa");
  document.documentElement.style.removeProperty("--narrativa-size");
});

describe("SettingsApplier", () => {
  it("escribe las variables CSS por defecto sobre <html>", () => {
    render(<SettingsApplier />);

    const root = document.documentElement;
    expect(root.style.getPropertyValue("--font-narrativa")).toBe(FONT_STACKS.serif);
    expect(root.style.getPropertyValue("--narrativa-size")).toBe(SIZE_VALUES.md);
  });

  it("refleja cambios de fuente y tamaño del store", () => {
    render(<SettingsApplier />);

    act(() => {
      useSettingsStore.getState().setNarrativaFont("dyslexic");
      useSettingsStore.getState().setNarrativaSize("lg");
    });

    const root = document.documentElement;
    expect(root.style.getPropertyValue("--font-narrativa")).toBe(FONT_STACKS.dyslexic);
    expect(root.style.getPropertyValue("--narrativa-size")).toBe(SIZE_VALUES.lg);
  });
});
