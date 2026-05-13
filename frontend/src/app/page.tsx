"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { List, Sparkles } from "lucide-react";
import { Header } from "@/components/header";
import { InicioDialog } from "@/components/inicio-dialog";
import { TurnoCard, StreamingTurnoCard } from "@/components/turno-card";
import { Acciones } from "@/components/acciones";
import { FinalBanner } from "@/components/final-banner";
import { PartidasList } from "@/components/partidas-list";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Loader } from "@/components/ui/loader";
import { api } from "@/lib/api";
import { usePartidaStore } from "@/store/partida-store";

export default function HomePage() {
  const [showInicio, setShowInicio] = useState(false);
  const [showPartidas, setShowPartidas] = useState(false);
  const [hidratado, setHidratado] = useState(false);
  const finalRef = useRef<HTMLDivElement>(null);

  const codigo = usePartidaStore((s) => s.codigoPartida);
  const historial = usePartidaStore((s) => s.historial);
  const estado = usePartidaStore((s) => s.estado);
  const final = usePartidaStore((s) => s.final);
  const razonFin = usePartidaStore((s) => s.razonFin);
  const isStreaming = usePartidaStore((s) => s.isStreaming);
  const streamingNarrativa = usePartidaStore((s) => s.streamingNarrativa);
  const imagenUltimoTurnoPendiente = usePartidaStore((s) => s.imagenUltimoTurnoPendiente);
  const hidratarDesdeBackend = usePartidaStore((s) => s.hidratarDesdeBackend);
  const resetear = usePartidaStore((s) => s.resetear);
  const establecerCodigo = usePartidaStore((s) => s.establecerCodigo);

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

  useEffect(() => {
    if (!necesitaHidratacion || !cargandoPartida) {
      setHidratado(true);
    }
  }, [necesitaHidratacion, cargandoPartida]);

  useEffect(() => {
    if (errorPartida) {
      resetear();
    }
  }, [errorPartida, resetear]);

  useEffect(() => {
    if (finalRef.current) {
      finalRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [historial.length]);

  const nuevaPartida = () => {
    resetear();
    setShowInicio(true);
  };

  const handleReanudar = (codigo: string) => {
    resetear();
    establecerCodigo(codigo);
    setShowPartidas(false);
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
          <BienvenidaVacia
            onComenzar={() => setShowInicio(true)}
            onVerPartidas={() => setShowPartidas(true)}
            onReanudar={handleReanudar}
          />
        ) : (
          <>
            {historial.map((turno, idx) => {
              const esUltimo = idx === historial.length - 1;
              return (
                <TurnoCard
                  key={turno.turno}
                  turno={turno}
                  esUltimo={esUltimo}
                  imagenCargando={esUltimo && imagenUltimoTurnoPendiente}
                />
              );
            })}

            {isStreaming && streamingNarrativa !== null && (
              <StreamingTurnoCard narrativa={streamingNarrativa} />
            )}

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

      <Dialog open={showPartidas} onOpenChange={setShowPartidas}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Partidas guardadas</DialogTitle>
          </DialogHeader>
          <PartidasList onReanudar={handleReanudar} />
        </DialogContent>
      </Dialog>
    </div>
  );
}

interface BienvenidaVaciaProps {
  onComenzar: () => void;
  onVerPartidas: () => void;
  onReanudar: (codigo: string) => void;
}

function BienvenidaVacia({ onComenzar, onVerPartidas, onReanudar }: BienvenidaVaciaProps) {
  const [codigoInput, setCodigoInput] = useState("");

  const handleReanudarManual = () => {
    const trimmed = codigoInput.trim();
    if (trimmed) {
      onReanudar(trimmed);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <Sparkles className="h-12 w-12 text-primary mb-4" />
      <h1 className="text-3xl font-bold mb-2 font-serif">Echoes</h1>
      <p className="text-muted-foreground mb-6 max-w-md">
        Aventuras interactivas generadas por IA, adaptadas a tus decisiones.
        Cada partida es única.
      </p>
      <Button size="lg" onClick={onComenzar} className="mb-6">
        Empezar aventura
      </Button>

      <div className="w-full max-w-sm space-y-3">
        <div className="flex items-center gap-2 text-muted-foreground text-sm">
          <div className="flex-1 border-t" />
          <span>o retomá una partida</span>
          <div className="flex-1 border-t" />
        </div>

        <div className="flex gap-2">
          <Input
            placeholder="Código de partida"
            value={codigoInput}
            onChange={(e) => setCodigoInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleReanudarManual(); }}
          />
          <Button
            variant="outline"
            onClick={handleReanudarManual}
            disabled={!codigoInput.trim()}
          >
            Reanudar
          </Button>
        </div>

        <Button
          variant="ghost"
          size="sm"
          className="w-full gap-2"
          onClick={onVerPartidas}
        >
          <List className="h-4 w-4" />
          Ver todas las partidas
        </Button>
      </div>
    </div>
  );
}
