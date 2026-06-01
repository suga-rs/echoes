import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiClientError, api, avanzarTurnoStream } from "@/lib/api";

function jsonResponse(body: unknown, ok = true, status = 200): Response {
  return { ok, status, json: async () => body } as Response;
}

function sseResponse(chunks: string[]): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const c of chunks) controller.enqueue(encoder.encode(c));
      controller.close();
    },
  });
  return { ok: true, status: 200, body } as unknown as Response;
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("api.request (vía api.*)", () => {
  it("devuelve el JSON en respuestas 2xx", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({ descripcion: "ok" })));

    const res = await api.generarDescripcionAleatoria("terror");

    expect(res).toEqual({ descripcion: "ok" });
  });

  it("lanza ApiClientError con status y code en respuestas no-2xx", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse(
          { code: "partida_no_encontrada", mensaje: "no existe", detalles: {} },
          false,
          404,
        ),
      ),
    );

    const err = await api.getEstado("abc").catch((e: unknown) => e);

    expect(err).toBeInstanceOf(ApiClientError);
    expect((err as ApiClientError).status).toBe(404);
    expect((err as ApiClientError).code).toBe("partida_no_encontrada");
  });
});

describe("avanzarTurnoStream", () => {
  it("parsea los eventos SSE y dispara los handlers correspondientes", async () => {
    const chunks = [
      'event: token\ndata: {"content": "Hola"}\n\n',
      'event: token\ndata: {"content": " mundo"}\n\n',
      'event: turno\ndata: {"turno": 2, "narrativa": "N", "opciones": ["a","b","c"],' +
        ' "estado": "en_curso", "final": null, "razon_fin": null, "imagen_pendiente": true}\n\n',
      'event: imagen\ndata: {"imagen_url": "http://img/2.png"}\n\n',
      "event: done\ndata: {}\n\n",
    ];
    vi.stubGlobal("fetch", vi.fn(async () => sseResponse(chunks)));

    const onToken = vi.fn();
    const onTurno = vi.fn();
    const onImagen = vi.fn();
    const onError = vi.fn();
    const onDone = vi.fn();

    await avanzarTurnoStream("abc", "ir", { onToken, onTurno, onImagen, onError, onDone });

    expect(onToken.mock.calls.map((c) => c[0])).toEqual(["Hola", " mundo"]);
    expect(onTurno).toHaveBeenCalledWith(
      expect.objectContaining({ turno: 2, imagen_pendiente: true }),
    );
    expect(onImagen).toHaveBeenCalledWith("http://img/2.png");
    expect(onDone).toHaveBeenCalledTimes(1);
    expect(onError).not.toHaveBeenCalled();
  });

  it("llama onError si la respuesta no es ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 500,
        body: null,
        json: async () => ({ code: "boom", mensaje: "explotó", detalles: {} }),
      })),
    );

    const onError = vi.fn();
    await avanzarTurnoStream("abc", "ir", {
      onToken: vi.fn(),
      onTurno: vi.fn(),
      onImagen: vi.fn(),
      onError,
      onDone: vi.fn(),
    });

    expect(onError).toHaveBeenCalledOnce();
    expect(onError.mock.calls[0][0]).toBeInstanceOf(ApiClientError);
  });
});
