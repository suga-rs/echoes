"use client";

import { useRef, useState } from "react";
import Image from "next/image";
import { Flag, ImagePlus, Loader2, Pause, Play } from "lucide-react";
import type { TurnoHistorial } from "@/lib/types";
import { ImagenModal } from "@/components/imagen-modal";
import { api, ApiClientError } from "@/lib/api";
import { usePartidaStore } from "@/store/partida-store";
import { useSettingsStore } from "@/store/settings-store";

interface TurnoCardProps {
  turno: TurnoHistorial;
  esUltimo: boolean;
  imagenCargando?: boolean;
}

export function TurnoCard({ turno, esUltimo, imagenCargando = false }: TurnoCardProps) {
  const [imagenAbierta, setImagenAbierta] = useState(false);
  const [generando, setGenerando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [limiteAlcanzado, setLimiteAlcanzado] = useState(false);
  const [marcado, setMarcado] = useState(turno.feedback === "incoherente");

  const [audioCargando, setAudioCargando] = useState(false);
  const [audioReproduciendo, setAudioReproduciendo] = useState(false);
  const [audioError, setAudioError] = useState<string | null>(null);
  // Audio element + URL cacheada por voz: replays no vuelven a pegarle a la API.
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioCacheRef = useRef<{ voice: string; url: string } | null>(null);

  const codigo = usePartidaStore((s) => s.codigoPartida);
  const actualizarImagenTurno = usePartidaStore((s) => s.actualizarImagenTurno);
  const narratorVoice = useSettingsStore((s) => s.narratorVoice);

  const marcarIncoherente = async () => {
    if (!codigo || marcado) return;
    setMarcado(true); // optimista
    try {
      await api.marcarFeedback(codigo, turno.turno);
    } catch {
      setMarcado(false);
    }
  };

  const reproducirAudio = async () => {
    if (!codigo || audioCargando) return;

    // Si ya está sonando, lo detenemos (toggle).
    if (audioReproduciendo) {
      audioRef.current?.pause();
      return;
    }

    setAudioError(null);

    // Reusamos la URL cacheada si es de la voz actual; si cambió la voz, refetch.
    let url = audioCacheRef.current?.voice === narratorVoice ? audioCacheRef.current.url : null;
    if (!url) {
      setAudioCargando(true);
      try {
        const { audio_url } = await api.generarAudioTurno(codigo, turno.turno, narratorVoice);
        url = audio_url;
        audioCacheRef.current = { voice: narratorVoice, url };
      } catch (err) {
        setAudioError(err instanceof Error ? err.message : "No se pudo generar el audio");
        return;
      } finally {
        setAudioCargando(false);
      }
    }

    let audio = audioRef.current;
    if (!audio || audio.src !== url) {
      audio = new Audio(url);
      audioRef.current = audio;
      audio.onplay = () => setAudioReproduciendo(true);
      audio.onpause = () => setAudioReproduciendo(false);
      audio.onended = () => setAudioReproduciendo(false);
    }
    try {
      await audio.play();
    } catch {
      // El navegador puede rechazar play() (p. ej. sin gesto del usuario); lo ignoramos.
    }
  };

  const generarImagen = async () => {
    if (!codigo || generando) return;
    setError(null);
    setGenerando(true);
    try {
      const { imagen_url } = await api.generarImagenTurno(codigo, turno.turno);
      actualizarImagenTurno(turno.turno, imagen_url);
    } catch (err) {
      if (err instanceof ApiClientError && err.code === "limite_imagenes_excedido") {
        setLimiteAlcanzado(true);
      } else {
        setError(err instanceof Error ? err.message : "No se pudo generar la imagen");
      }
    } finally {
      setGenerando(false);
    }
  };

  return (
    <article className="animate-fade-in mb-8">
      {turno.accion_jugador !== "<inicio>" && (
        <div className="mb-4 flex justify-end">
          <div className="fuente-narrativa bg-primary/15 text-foreground px-4 py-2 rounded-2xl rounded-tr-sm max-w-[80%] text-sm">
            <span className="text-xs text-muted-foreground block mb-0.5">Tu acción:</span>
            {turno.accion_jugador}
          </div>
        </div>
      )}

      {turno.imagen_url ? (
        <>
          <button
            type="button"
            onClick={() => setImagenAbierta(true)}
            className="relative w-full aspect-[3/2] mb-4 rounded-lg overflow-hidden bg-muted cursor-pointer hover:opacity-90 transition-opacity block"
          >
            <Image
              src={turno.imagen_url}
              alt={`Escena del turno ${turno.turno}`}
              fill
              className="object-cover"
              sizes="(max-width: 768px) 100vw, 768px"
              priority={esUltimo}
              unoptimized
            />
          </button>
          <ImagenModal
            src={turno.imagen_url}
            open={imagenAbierta}
            onClose={() => setImagenAbierta(false)}
            alt={`Escena del turno ${turno.turno}`}
          />
        </>
      ) : imagenCargando || generando ? (
        <div className="w-full aspect-[3/2] mb-4 rounded-lg bg-muted animate-pulse" />
      ) : null}

      <div className="bg-card rounded-lg p-5 border">
        <div className="flex items-center justify-between mb-2">
          <div className="text-xs text-muted-foreground uppercase tracking-wide">
            Turno {turno.turno}
          </div>
          <div className="flex items-center gap-3">
            {!turno.imagen_url && !generando && !imagenCargando && !limiteAlcanzado && (
              <button
                type="button"
                onClick={() => void generarImagen()}
                aria-label="Ilustrar esta escena"
                title="Ilustrar esta escena"
                className="text-muted-foreground hover:text-primary flex items-center"
              >
                <ImagePlus className="h-4 w-4" />
              </button>
            )}
            <button
              type="button"
              onClick={() => void marcarIncoherente()}
              disabled={marcado}
              aria-label="Marcar turno como incoherente"
              className="text-xs text-muted-foreground hover:text-destructive flex items-center gap-1 disabled:opacity-60"
            >
              <Flag className="h-3 w-3" />
              {marcado ? "Marcado" : "Incoherente"}
            </button>
          </div>
        </div>
        {limiteAlcanzado && (
          <p className="text-xs text-muted-foreground mb-2">
            Alcanzaste el límite de imágenes de esta partida.
          </p>
        )}
        {error && <p className="text-xs text-destructive mb-2">{error}</p>}
        <p className="narrativa whitespace-pre-wrap">{turno.narrativa}</p>

        <div className="mt-3 flex items-center gap-2">
          <button
            type="button"
            onClick={() => void reproducirAudio()}
            disabled={audioCargando}
            aria-label={audioReproduciendo ? "Detener la narración" : "Escuchar la narración"}
            title={audioReproduciendo ? "Detener la narración" : "Escuchar la narración"}
            className="text-muted-foreground hover:text-primary flex items-center disabled:opacity-60"
          >
            {audioCargando ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : audioReproduciendo ? (
              <Pause className="h-4 w-4" />
            ) : (
              <Play className="h-4 w-4" />
            )}
          </button>
          {audioError && <span className="text-xs text-destructive">{audioError}</span>}
        </div>
      </div>
    </article>
  );
}

interface StreamingTurnoCardProps {
  narrativa: string;
}

export function StreamingTurnoCard({ narrativa }: StreamingTurnoCardProps) {
  return (
    <article className="mb-8">
      <div className="bg-card rounded-lg p-5 border">
        <div className="text-xs text-muted-foreground uppercase tracking-wide mb-2">
          Generando...
        </div>
        <p className="narrativa whitespace-pre-wrap">
          {narrativa}
          <span className="inline-block w-0.5 h-4 bg-foreground ml-0.5 align-text-bottom animate-pulse" />
        </p>
      </div>
    </article>
  );
}
