"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { ArrowLeft, Camera, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Loader } from "@/components/ui/loader";
import { PartidasList } from "@/components/partidas-list";
import { api, ApiClientError } from "@/lib/api";
import { useAuthStore } from "@/store/auth-store";
import { usePartidaStore } from "@/store/partida-store";
import { formatFechaHora } from "@/lib/utils";

export default function PerfilPage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const resetear = usePartidaStore((s) => s.resetear);
  const establecerCodigo = usePartidaStore((s) => s.establecerCodigo);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [hidratado, setHidratado] = useState(false);

  // Zustand con persist se hidrata en cliente; esperamos un tick para no
  // redirigir antes de leer el usuario persistido.
  useEffect(() => {
    setHidratado(true);
  }, []);

  useEffect(() => {
    if (hidratado && !user) {
      router.replace("/");
    }
  }, [hidratado, user, router]);

  const avatarMutation = useMutation({
    mutationFn: (file: File) => api.uploadAvatar(file),
    onSuccess: (data) => {
      if (user) setUser({ ...user, avatar_url: data.avatar_url });
    },
  });

  const reanudar = (codigo: string) => {
    resetear();
    establecerCodigo(codigo);
    router.push("/");
  };

  if (!hidratado || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader message="Cargando perfil..." />
      </div>
    );
  }

  const error = avatarMutation.error as ApiClientError | null;

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b bg-background/95 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center gap-3 px-4 py-3">
          <Button variant="ghost" size="icon" onClick={() => router.push("/")} title="Volver">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-sm font-semibold">Mi perfil</h1>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-6">
        <section className="mb-8 flex items-center gap-4">
          <div className="relative">
            <div className="flex h-20 w-20 items-center justify-center overflow-hidden rounded-full border bg-muted">
              {user.avatar_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={user.avatar_url}
                  alt={user.username}
                  className="h-full w-full object-cover"
                />
              ) : (
                <User className="h-8 w-8 text-muted-foreground" />
              )}
            </div>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={avatarMutation.isPending}
              className="absolute -bottom-1 -right-1 rounded-full border bg-background p-1.5 shadow-sm hover:bg-accent disabled:opacity-50"
              title="Cambiar avatar"
            >
              <Camera className="h-3.5 w-3.5" />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) avatarMutation.mutate(file);
                e.target.value = "";
              }}
            />
          </div>

          <div className="min-w-0">
            <h2 className="truncate text-2xl font-bold font-serif">{user.username}</h2>
            <p className="text-sm text-muted-foreground">
              Miembro desde {formatFechaHora(user.creada_en)}
            </p>
            {avatarMutation.isPending && (
              <p className="text-xs text-muted-foreground">Subiendo avatar...</p>
            )}
            {error && (
              <p className="text-xs text-destructive">
                {error.code === "contenido_inapropiado"
                  ? "Imagen no válida (usá PNG/JPEG/WebP, máx. 5 MB)."
                  : "No se pudo subir el avatar."}
              </p>
            )}
          </div>
        </section>

        <section>
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Mis aventuras
          </h3>
          <PartidasList onReanudar={reanudar} />
        </section>
      </main>
    </div>
  );
}
