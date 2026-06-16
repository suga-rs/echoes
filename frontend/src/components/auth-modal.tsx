"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiClientError } from "@/lib/api";
import { useAuthStore } from "@/store/auth-store";

type Modo = "login" | "register";

interface AuthModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AuthModal({ open, onOpenChange }: AuthModalProps) {
  const [modo, setModo] = useState<Modo>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const login = useAuthStore((s) => s.login);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async () => {
      const fn = modo === "login" ? api.login : api.register;
      return fn(username.trim(), password);
    },
    onSuccess: (data) => {
      login(data.access_token, data.user);
      queryClient.invalidateQueries({ queryKey: ["partidas"] });
      reset();
      onOpenChange(false);
    },
  });

  const reset = () => {
    setUsername("");
    setPassword("");
    mutation.reset();
  };

  const cambiarModo = (nuevo: Modo) => {
    setModo(nuevo);
    mutation.reset();
  };

  const error = mutation.error as ApiClientError | null;
  const minLenOk =
    modo === "login" || (username.trim().length >= 3 && password.length >= 8);
  const puedeEnviar = username.trim().length > 0 && password.length > 0 && minLenOk;

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) reset();
        onOpenChange(o);
      }}
    >
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>
            {modo === "login" ? "Iniciar sesión" : "Crear cuenta"}
          </DialogTitle>
          <DialogDescription>
            {modo === "login"
              ? "Accedé para ver tus aventuras."
              : "Elegí un nombre de usuario y una contraseña."}
          </DialogDescription>
        </DialogHeader>

        <form
          className="grid gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (puedeEnviar) mutation.mutate();
          }}
        >
          <div className="grid gap-1.5">
            <Label htmlFor="auth-username">Usuario</Label>
            <Input
              id="auth-username"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="tu_usuario"
            />
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="auth-password">Contraseña</Label>
            <Input
              id="auth-password"
              type="password"
              autoComplete={modo === "login" ? "current-password" : "new-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
            {modo === "register" && (
              <p className="text-xs text-muted-foreground">
                Mínimo 8 caracteres. El usuario, entre 3 y 32.
              </p>
            )}
          </div>

          {error && (
            <p className="text-sm text-destructive">
              {error.code === "credenciales_invalidas"
                ? "Usuario o contraseña incorrectos."
                : error.code === "usuario_ya_existe"
                  ? "Ese nombre de usuario ya está en uso."
                  : error.message}
            </p>
          )}

          <Button type="submit" disabled={!puedeEnviar || mutation.isPending}>
            {mutation.isPending
              ? "Procesando..."
              : modo === "login"
                ? "Entrar"
                : "Registrarme"}
          </Button>
        </form>

        <div className="text-center text-sm text-muted-foreground">
          {modo === "login" ? (
            <>
              ¿No tenés cuenta?{" "}
              <button
                type="button"
                className="text-primary underline-offset-4 hover:underline"
                onClick={() => cambiarModo("register")}
              >
                Crear una
              </button>
            </>
          ) : (
            <>
              ¿Ya tenés cuenta?{" "}
              <button
                type="button"
                className="text-primary underline-offset-4 hover:underline"
                onClick={() => cambiarModo("login")}
              >
                Iniciar sesión
              </button>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
