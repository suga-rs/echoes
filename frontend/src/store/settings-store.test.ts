import { beforeEach, describe, expect, it } from "vitest";
import {
  SETTINGS_STORAGE_KEY,
  useSettingsStore,
} from "@/store/settings-store";

beforeEach(() => {
  localStorage.clear();
  useSettingsStore.setState({
    narrativaFont: "serif",
    narrativaSize: "md",
    narratorVoice: "alloy",
  });
});

describe("settings-store", () => {
  it("usa serif y tamaño medio por defecto", () => {
    const s = useSettingsStore.getState();
    expect(s.narrativaFont).toBe("serif");
    expect(s.narrativaSize).toBe("md");
  });

  it("setNarrativaFont actualiza la fuente", () => {
    useSettingsStore.getState().setNarrativaFont("dyslexic");
    expect(useSettingsStore.getState().narrativaFont).toBe("dyslexic");
  });

  it("setNarrativaSize actualiza el tamaño", () => {
    useSettingsStore.getState().setNarrativaSize("lg");
    expect(useSettingsStore.getState().narrativaSize).toBe("lg");
  });

  it("usa alloy como voz del narrador por defecto", () => {
    expect(useSettingsStore.getState().narratorVoice).toBe("alloy");
  });

  it("setNarratorVoice actualiza la voz", () => {
    useSettingsStore.getState().setNarratorVoice("nova");
    expect(useSettingsStore.getState().narratorVoice).toBe("nova");
  });

  it("persiste las preferencias en localStorage bajo la clave esperada", () => {
    useSettingsStore.getState().setNarrativaFont("sans");
    useSettingsStore.getState().setNarrativaSize("sm");
    useSettingsStore.getState().setNarratorVoice("shimmer");

    const raw = localStorage.getItem(SETTINGS_STORAGE_KEY);
    expect(raw).toBeTruthy();
    const persisted = JSON.parse(raw as string).state;
    expect(persisted.narrativaFont).toBe("sans");
    expect(persisted.narrativaSize).toBe("sm");
    expect(persisted.narratorVoice).toBe("shimmer");
  });
});
