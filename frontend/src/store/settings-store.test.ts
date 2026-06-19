import { beforeEach, describe, expect, it } from "vitest";
import {
  SETTINGS_STORAGE_KEY,
  useSettingsStore,
} from "@/store/settings-store";

beforeEach(() => {
  localStorage.clear();
  useSettingsStore.setState({ narrativaFont: "serif", narrativaSize: "md" });
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

  it("persiste las preferencias en localStorage bajo la clave esperada", () => {
    useSettingsStore.getState().setNarrativaFont("sans");
    useSettingsStore.getState().setNarrativaSize("sm");

    const raw = localStorage.getItem(SETTINGS_STORAGE_KEY);
    expect(raw).toBeTruthy();
    const persisted = JSON.parse(raw as string).state;
    expect(persisted.narrativaFont).toBe("sans");
    expect(persisted.narrativaSize).toBe("sm");
  });
});
