import { beforeEach, describe, expect, it } from "vitest";
import type { Personaje, TurnoHistorial } from "@/lib/types";
import { usePartidaStore } from "@/store/partida-store";

const personaje: Personaje = {
  nombre: "Lyra",
  descripcion_narrativa: "Arqueóloga escéptica.",
  descripcion_visual_en: "Woman around 40.",
  inventario: ["linterna", "diario"],
};

const turno = (n: number, extra: Partial<TurnoHistorial> = {}): TurnoHistorial => ({
  turno: n,
  accion_jugador: "<inicio>",
  narrativa: `Narrativa ${n}`,
  opciones: ["a", "b", "c"],
  imagen_url: null,
  ...extra,
});

beforeEach(() => {
  usePartidaStore.getState().resetear();
});

describe("partida-store", () => {
  it("iniciarPartida setea código, personaje, inventario e historial", () => {
    usePartidaStore.getState().iniciarPartida({
      codigo: "abc",
      personaje,
      objetivo: "Encontrar el corazón",
      primerTurno: turno(1),
    });

    const s = usePartidaStore.getState();
    expect(s.codigoPartida).toBe("abc");
    expect(s.personaje?.nombre).toBe("Lyra");
    expect(s.inventario).toEqual(["linterna", "diario"]);
    expect(s.historial).toHaveLength(1);
    expect(s.estado).toBe("en_curso");
  });

  it("agregarTurno suma al historial en orden", () => {
    usePartidaStore.getState().iniciarPartida({
      codigo: "abc",
      personaje,
      objetivo: "Obj",
      primerTurno: turno(1),
    });
    usePartidaStore.getState().agregarTurno(turno(2, { accion_jugador: "ir al norte" }));

    expect(usePartidaStore.getState().historial.map((t) => t.turno)).toEqual([1, 2]);
  });

  it("appendStreamToken concatena los tokens recibidos", () => {
    usePartidaStore.getState().iniciarStreaming();
    usePartidaStore.getState().appendStreamToken("Hola ");
    usePartidaStore.getState().appendStreamToken("mundo");

    expect(usePartidaStore.getState().streamingNarrativa).toBe("Hola mundo");
  });

  it("finalizarStreaming retiene el turno para el revelado y commitea al terminar", () => {
    usePartidaStore.getState().iniciarStreaming();
    usePartidaStore.getState().appendStreamToken("...");
    usePartidaStore.getState().finalizarStreaming(turno(2), true);

    // Aún no commiteado: queda pendiente para el revelado typewriter.
    expect(usePartidaStore.getState().turnoPendiente?.turno.turno).toBe(2);
    expect(usePartidaStore.getState().historial).toHaveLength(0);

    // Al terminar el typewriter, el turno se vuelca y se limpian los flags.
    usePartidaStore.getState().commitTurnoPendiente();
    const s = usePartidaStore.getState();
    expect(s.isStreaming).toBe(false);
    expect(s.streamingNarrativa).toBeNull();
    expect(s.imagenUltimoTurnoPendiente).toBe(true);
    expect(s.historial.at(-1)?.turno).toBe(2);
  });

  it("actualizarImagenTurno actualiza solo el turno que matchea y baja el flag", () => {
    usePartidaStore.getState().iniciarPartida({
      codigo: "abc",
      personaje,
      objetivo: "Obj",
      primerTurno: turno(1),
    });
    usePartidaStore.getState().agregarTurno(turno(2));
    usePartidaStore.getState().actualizarImagenTurno(2, "http://img/2.png");

    const h = usePartidaStore.getState().historial;
    expect(h.find((t) => t.turno === 1)?.imagen_url).toBeNull();
    expect(h.find((t) => t.turno === 2)?.imagen_url).toBe("http://img/2.png");
    expect(usePartidaStore.getState().imagenUltimoTurnoPendiente).toBe(false);
  });

  it("hidratarDesdeBackend reemplaza el estado completo", () => {
    usePartidaStore.getState().hidratarDesdeBackend({
      codigo: "xyz",
      personaje,
      objetivo: "Obj",
      ubicacion: "Cripta",
      inventario: ["llave"],
      historial: [turno(1), turno(2)],
      estado: "en_curso",
      final: null,
      razonFin: null,
    });

    const s = usePartidaStore.getState();
    expect(s.codigoPartida).toBe("xyz");
    expect(s.ubicacion).toBe("Cripta");
    expect(s.inventario).toEqual(["llave"]);
    expect(s.historial).toHaveLength(2);
  });

  it("resetear limpia todo el estado", () => {
    usePartidaStore.getState().iniciarPartida({
      codigo: "abc",
      personaje,
      objetivo: "Obj",
      primerTurno: turno(1),
    });
    usePartidaStore.getState().resetear();

    const s = usePartidaStore.getState();
    expect(s.codigoPartida).toBeNull();
    expect(s.historial).toEqual([]);
    expect(s.estado).toBeNull();
  });
});

const tiradaFixture = {
  habilidad: "destreza",
  banda: "media",
  dc: 15,
  d20: 14,
  modificador: 3,
  total: 17,
  resultado: "exito",
} as const;

const get = () => usePartidaStore.getState();

describe("partida-store: buffering de la tirada", () => {
  it("retiene el turno (no toca el historial ni cierra el modal) si la tirada está abierta", () => {
    get().iniciarStreaming();
    get().iniciarTirada(tiradaFixture);
    get().finalizarStreaming(turno(2), false, null);

    expect(get().turnoPendiente?.turno.turno).toBe(2);
    expect(get().historial).toHaveLength(0);
    expect(get().tiradaActual).not.toBeNull(); // modal sigue abierto
  });

  it("al cerrar el modal con turno retenido, arranca el replay y luego commitea", () => {
    get().iniciarStreaming();
    get().iniciarTirada(tiradaFixture);
    get().finalizarStreaming(turno(2), false, {
      estado: "finalizada",
      final: "exito",
      razon: "ganaste",
    });

    get().cerrarTirada();
    expect(get().tiradaActual).toBeNull();
    expect(get().isStreaming).toBe(true);
    expect(get().streamingNarrativa).toBe("");
    expect(get().turnoPendiente).not.toBeNull();

    get().commitTurnoPendiente();
    expect(get().historial.map((t) => t.turno)).toContain(2);
    expect(get().turnoPendiente).toBeNull();
    expect(get().isStreaming).toBe(false);
    expect(get().estado).toBe("finalizada");
    expect(get().final).toBe("exito");
    expect(get().razonFin).toBe("ganaste");
  });

  it("cierre temprano (sin turno aún): al llegar el turno arranca el revelado y commitea", () => {
    get().iniciarStreaming();
    get().iniciarTirada(tiradaFixture);
    get().appendStreamToken("parcial");

    get().cerrarTirada(); // turnoPendiente es null
    expect(get().tiradaActual).toBeNull();
    expect(get().streamingNarrativa).toBe("parcial");

    // El turno llega luego: arranca el revelado typewriter (no commitea de una).
    get().finalizarStreaming(turno(2), false, null);
    expect(get().turnoPendiente?.turno.turno).toBe(2);
    expect(get().streamingNarrativa).toBe("");
    expect(get().historial).toHaveLength(0);

    get().commitTurnoPendiente();
    expect(get().historial.map((t) => t.turno)).toContain(2);
    expect(get().streamingNarrativa).toBeNull();
  });

  it("la imagen que llega con el turno retenido se guarda en el turno pendiente", () => {
    get().iniciarStreaming();
    get().iniciarTirada(tiradaFixture);
    get().finalizarStreaming(turno(2), true, null);

    get().actualizarImagenTurno(2, "http://img/2.png");
    expect(get().turnoPendiente?.turno.imagen_url).toBe("http://img/2.png");
    expect(get().turnoPendiente?.imagenPendiente).toBe(false);

    get().commitTurnoPendiente();
    expect(get().historial.find((t) => t.turno === 2)?.imagen_url).toBe("http://img/2.png");
  });
});
