import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiClientError } from "@/lib/api";
import type { TurnoHistorial } from "@/lib/types";
import { TurnoCard } from "@/components/turno-card";
import { usePartidaStore } from "@/store/partida-store";

vi.mock("next/image", () => ({
  default: ({ src, alt }: { src: string; alt: string }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt} />
  ),
}));

vi.mock("@/lib/api", () => ({
  api: {
    generarImagenTurno: vi.fn(),
    marcarFeedback: vi.fn().mockResolvedValue({ feedback: "incoherente" }),
  },
  ApiClientError: class ApiClientError extends Error {
    code: string;
    constructor(status: number, code: string, message: string) {
      super(message);
      this.code = code;
    }
  },
}));

beforeEach(() => {
  vi.clearAllMocks();
  usePartidaStore.getState().resetear();
});

const base: TurnoHistorial = {
  turno: 3,
  accion_jugador: "abrir la puerta",
  narrativa: "La puerta cruje al abrirse.",
  opciones: ["a", "b", "c"],
  imagen_url: null,
};

describe("TurnoCard", () => {
  it("renderiza la narrativa y el número de turno", () => {
    render(<TurnoCard turno={base} esUltimo={false} />);

    expect(screen.getByText("La puerta cruje al abrirse.")).toBeInTheDocument();
    expect(screen.getByText(/Turno 3/)).toBeInTheDocument();
  });

  it("muestra la acción del jugador salvo en el turno <inicio>", () => {
    const { rerender } = render(<TurnoCard turno={base} esUltimo={false} />);
    expect(screen.getByText("abrir la puerta")).toBeInTheDocument();

    rerender(<TurnoCard turno={{ ...base, accion_jugador: "<inicio>" }} esUltimo={false} />);
    expect(screen.queryByText("<inicio>")).not.toBeInTheDocument();
  });

  it("aplica la fuente del narrador (no el tamaño) a la acción del jugador", () => {
    render(<TurnoCard turno={base} esUltimo={false} />);

    const burbuja = screen.getByText("abrir la puerta");
    // Comparte la familia tipográfica del narrador...
    expect(burbuja).toHaveClass("fuente-narrativa");
    // ...pero no la clase .narrativa, que es la que arrastra el tamaño configurable.
    expect(burbuja).not.toHaveClass("narrativa");
  });

  it("ofrece el control de imagen en el header cuando el turno no tiene imagen_url", () => {
    render(<TurnoCard turno={base} esUltimo={false} />);

    expect(
      screen.getByRole("button", { name: /Ilustrar esta escena/ }),
    ).toBeInTheDocument();
  });

  it("oculta el control de imagen cuando el turno ya tiene imagen_url", () => {
    render(
      <TurnoCard
        turno={{ ...base, imagen_url: "https://example.com/x.png" }}
        esUltimo={false}
      />,
    );

    expect(
      screen.queryByRole("button", { name: /Ilustrar esta escena/ }),
    ).not.toBeInTheDocument();
  });

  it("muestra el esqueleto y oculta el control mientras genera la imagen", async () => {
    const user = userEvent.setup();
    usePartidaStore.getState().establecerCodigo("abc-123");
    // Promesa que no resuelve: el componente queda en estado "generando".
    vi.mocked(api.generarImagenTurno).mockReturnValue(new Promise(() => {}));

    const { container } = render(<TurnoCard turno={base} esUltimo={false} />);
    await user.click(screen.getByRole("button", { name: /Ilustrar esta escena/ }));

    expect(container.querySelector(".animate-pulse")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Ilustrar esta escena/ }),
    ).not.toBeInTheDocument();
  });

  it("muestra un error si la generación de imagen falla", async () => {
    const user = userEvent.setup();
    usePartidaStore.getState().establecerCodigo("abc-123");
    vi.mocked(api.generarImagenTurno).mockRejectedValue(new Error("boom"));

    render(<TurnoCard turno={base} esUltimo={false} />);
    await user.click(screen.getByRole("button", { name: /Ilustrar esta escena/ }));

    expect(await screen.findByText("boom")).toBeInTheDocument();
  });

  it("muestra el mensaje de límite y oculta el control al exceder el cupo", async () => {
    const user = userEvent.setup();
    usePartidaStore.getState().establecerCodigo("abc-123");
    vi.mocked(api.generarImagenTurno).mockRejectedValue(
      new ApiClientError(409, "limite_imagenes_excedido", "límite"),
    );

    render(<TurnoCard turno={base} esUltimo={false} />);
    await user.click(screen.getByRole("button", { name: /Ilustrar esta escena/ }));

    expect(
      await screen.findByText(/Alcanzaste el límite de imágenes/),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Ilustrar esta escena/ }),
    ).not.toBeInTheDocument();
  });

  it("marca el turno como incoherente llamando a la API", async () => {
    const user = userEvent.setup();
    usePartidaStore.getState().establecerCodigo("abc-123");
    render(<TurnoCard turno={base} esUltimo={false} />);

    await user.click(screen.getByRole("button", { name: /Marcar turno como incoherente/ }));

    expect(api.marcarFeedback).toHaveBeenCalledWith("abc-123", 3);
  });
});
