import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { SettingsSheet } from "@/components/settings-sheet";
import { useSettingsStore } from "@/store/settings-store";

beforeEach(() => {
  useSettingsStore.setState({
    narrativaFont: "serif",
    narrativaSize: "md",
    diceScheme: "marfil",
  });
});

describe("SettingsSheet", () => {
  it("seleccionar una fuente actualiza el store", async () => {
    const user = userEvent.setup();
    render(<SettingsSheet open onOpenChange={() => {}} />);

    await user.click(screen.getByRole("button", { name: "Dislexia" }));

    expect(useSettingsStore.getState().narrativaFont).toBe("dyslexic");
  });

  it("seleccionar un tamaño actualiza el store", async () => {
    const user = userEvent.setup();
    render(<SettingsSheet open onOpenChange={() => {}} />);

    await user.click(screen.getByRole("button", { name: "Grande" }));

    expect(useSettingsStore.getState().narrativaSize).toBe("lg");
  });

  it("ofrece tres esquemas de dado y seleccionar uno actualiza el store", async () => {
    const user = userEvent.setup();
    render(<SettingsSheet open onOpenChange={() => {}} />);

    expect(screen.getByRole("button", { name: "Carmesí" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Esmerald" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Zafiro" }));

    expect(useSettingsStore.getState().diceScheme).toBe("obsidiana");
  });
});
