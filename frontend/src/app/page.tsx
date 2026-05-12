"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { Header } from "@/components/header";
import { InicioDialog } from "@/components/inicio-dialog";
import { TurnoCard } from "@/components/turno-card";
import { Acciones } from "@/components/acciones";
import { FinalBanner } from "@/components/final-banner";
import { Button } from "@/components/ui/button";
import { Loader } from "@/components/ui/loader";
import { api } from "@/lib/api";
import { usePartidaStore } from "@/store/partida-store";

export default function HomePage() {
  const [showInicio, setShowInicio] = useState(false);
  const [hidratado, setHidratado] = useState(false);
  const finalRef = useRef<HTMLDivElement>(null);

  const codigo = usePartidaStore((s) => s.codigoPartida);
  const historial = usePartidaStore((s) => s.historial);
  const estado = usePartidaStore((s) => s.estado);
  const final = usePartidaStore((s) => s.final);
  const razonFin = usePartidaStore((s) => s.razonFin);
  const hidratarDesdeBackend = usePartidaStore((s) => s.hidratarDesdeBackend);
  const resetear = usePartidaStore((s) => s.resetear);

  // Hidratar partida desde backend si hay código pero no historial
  const necesitaHidratacion = codigo !== null && historial.length === 0;
  const { isLoading: cargandoPartida, error: errorPartida } = useQuery({
    queryKey: ["partida", codigo],
    queryFn: async () => {
      if (!codigo) return null;
      const partida = await api.reanudarPartida(codigo);
      hidratarDesdeBackend({
        codigo: partida.codigo_partida,
        personaje: partida.personaje,
        objetivo: partida.world_state.objetivo,
        ubicacion: partida.world_state.ubicacion_actual,
        inventario: partida.personaje.inventario,
        historial: partida.historial,
        estado: partida.metadata.estado,
        final: partida.metadata.final,
        razonFin: partida.metadata.razon_fin,
      });
      return partida;
    },
    enabled: necesitaHidratacion,
    retry: false,
  });

  // Marcar hidratación lista (evita pestañeo del modal de inicio)
  useEffect(() => {
    if (!necesitaHidratacion || !cargandoPartida) {
      setHidratado(true);
    }
  }, [necesitaHidratacion, cargandoPartida]);

  // Si la hidratación falla (código viejo), resetear
  useEffect(() => {
    if (errorPartida) {
      resetear();
    }
  }, [errorPartida, resetear]);

  // Scroll al final cuando se agrega un turno
  useEffect(() => {
    if (finalRef.current) {
      finalRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [historial.length]);

  const nuevaPartida = () => {
    resetear();
    setShowInicio(true);
  };

  const ultimoTurno = historial[historial.length - 1];
  const sinPartida = hidratado && !codigo;

  return (
    <div className="min-h-screen flex flex-col">
      <Header onNuevaPartida={nuevaPartida} />

      <main className="flex-1 max-w-3xl w-full mx-auto px-4 py-6">
        {!hidratado || cargandoPartida ? (
          <div className="flex items-center justify-center min-h-[50vh]">
            <Loader message="Cargando tu aventura..." />
          </div>
        ) : sinPartida ? (
          <BienvenidaVacia onComenzar={() => setShowInicio(true)} />
        ) : (
          <>
            {historial.map((turno, idx) => (
              <TurnoCard
                key={turno.turno}
                turno={turno}
                esUltimo={idx === historial.length - 1}
              />
            ))}

            {estado === "en_curso" && ultimoTurno && (
              <Acciones opciones={ultimoTurno.opciones} />
            )}

            {estado === "finalizada" && (
              <FinalBanner
                final={final}
                razon={razonFin}
                onNuevaPartida={nuevaPartida}
              />
            )}

            <div ref={finalRef} />
          </>
        )}
      </main>

      <InicioDialog open={showInicio} onOpenChange={setShowInicio} />
    </div>
  );
}

function BienvenidaVacia({ onComenzar }: { onComenzar: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <Sparkles className="h-12 w-12 text-primary mb-4" />
      <h1 className="text-3xl font-bold mb-2 font-serif">Echoes</h1>
      <p className="text-muted-foreground mb-6 max-w-md">
        Aventuras interactivas generadas por IA, adaptadas a tus decisiones.
        Cada partida es única.
      </p>
      <Button size="lg" onClick={onComenzar}>
        Empezar aventura
      </Button>
    </div>
  );
}
