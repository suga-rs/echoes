"use client";

import { useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { Plus, Package, PanelLeft, Home, LogIn, LogOut, User, Settings, ChevronDown, Heart } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { usePartidaStore } from "@/store/partida-store";
import { useAuthStore } from "@/store/auth-store";
import { AuthModal } from "./auth-modal";
import { SettingsSheet } from "./settings-sheet";
import { FichaAtributos } from "./ficha-atributos";
import { BarraVida } from "./barra-vida";

const capitalizar = (texto: string) =>
  texto.charAt(0).toUpperCase() + texto.slice(1);

interface HeaderProps {
  onNuevaPartida: () => void;
  onToggleSidebar?: () => void;
  onVolverAlInicio?: () => void;
}

export function Header({ onNuevaPartida, onToggleSidebar, onVolverAlInicio }: HeaderProps) {
  const [showInventario, setShowInventario] = useState(false);
  const [showAuth, setShowAuth] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const codigo = usePartidaStore((s) => s.codigoPartida);
  const objetivo = usePartidaStore((s) => s.objetivo);
  const personaje = usePartidaStore((s) => s.personaje);
  const inventario = usePartidaStore((s) => s.inventario);
  const pvActual = usePartidaStore((s) => s.pvActual);
  const pvMax = usePartidaStore((s) => s.pvMax);
  const condiciones = usePartidaStore((s) => s.condiciones);
  const danoUltimoTurno = usePartidaStore((s) => s.danoUltimoTurno);
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const queryClient = useQueryClient();

  const cerrarSesion = () => {
    logout();
    queryClient.invalidateQueries({ queryKey: ["partidas"] });
  };

  return (
    <header className="sticky top-0 z-30 bg-background/95 backdrop-blur border-b">
      <div className="max-w-3xl mx-auto px-4 py-3 flex items-center gap-3">
        {codigo && onToggleSidebar && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleSidebar}
            title="Ver partidas"
          >
            <PanelLeft className="h-4 w-4" />
          </Button>
        )}

        <div className="flex-1 min-w-0">
          {objetivo ? (
            <>
              <div className="text-xs text-muted-foreground uppercase tracking-wide">
                Objetivo
              </div>
              <div className="fuente-narrativa text-sm font-medium truncate">{capitalizar(objetivo)}</div>
            </>
          ) : (
            <div className="text-sm font-semibold">Echoes</div>
          )}
        </div>

        {codigo && pvActual !== null && pvMax !== null && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowInventario(true)}
            title="Ver ficha"
            className={pvActual <= pvMax * 0.25 ? "text-red-600" : undefined}
          >
            <Heart className="h-4 w-4" />
            <span className="ml-1 font-mono text-xs">
              {pvActual}/{pvMax}
            </span>
            {condiciones.length > 0 && (
              <span className="ml-1 h-1.5 w-1.5 rounded-full bg-red-600" aria-hidden />
            )}
          </Button>
        )}

        {codigo && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowInventario(true)}
            title="Ver inventario"
          >
            <Package className="h-4 w-4" />
            <span className="ml-1 text-xs">{inventario.length}</span>
          </Button>
        )}

        {user ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" title="Menú de usuario">
                {user.avatar_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={user.avatar_url}
                    alt={user.username}
                    className="h-6 w-6 rounded-full object-cover"
                  />
                ) : (
                  <User className="h-4 w-4" />
                )}
                <span className="text-xs max-w-24 truncate ml-2">{user.username}</span>
                <ChevronDown className="h-3 w-3 ml-1 opacity-70" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link href="/perfil">
                  <User className="h-4 w-4" />
                  Ir al perfil
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={() => setShowSettings(true)}>
                <Settings className="h-4 w-4" />
                Ajustes
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={cerrarSesion}>
                <LogOut className="h-4 w-4" />
                Cerrar sesión
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : (
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAuth(true)}
              title="Iniciar sesión"
            >
              <LogIn className="h-4 w-4 mr-1" />
              <span className="text-xs">Iniciar sesión</span>
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setShowSettings(true)}
              title="Ajustes"
            >
              <Settings className="h-4 w-4" />
            </Button>
          </>
        )}

        {codigo && onVolverAlInicio && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onVolverAlInicio}
            title="Volver al inicio"
          >
            <Home className="h-4 w-4" />
          </Button>
        )}

        <Button size="sm" onClick={onNuevaPartida} title="Nueva aventura">
          <Plus className="h-4 w-4 mr-1" />
          Nueva
        </Button>
      </div>

      <Dialog open={showInventario} onOpenChange={setShowInventario}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Ficha de {personaje?.nombre}</DialogTitle>
            <DialogDescription className="fuente-narrativa">
              {personaje?.descripcion_narrativa}
            </DialogDescription>
          </DialogHeader>
          {pvActual !== null && pvMax !== null && (
            <div className="mb-3">
              <BarraVida
                pvActual={pvActual}
                pvMax={pvMax}
                condiciones={condiciones}
                danoUltimoTurno={danoUltimoTurno}
              />
            </div>
          )}
          {personaje?.atributos && (
            <div className="mb-3">
              <div className="text-xs text-muted-foreground uppercase tracking-wide mb-2">
                Atributos
              </div>
              <FichaAtributos atributos={personaje.atributos} />
            </div>
          )}
          <div className="text-xs text-muted-foreground uppercase tracking-wide mb-2">
            Inventario
          </div>
          {inventario.length === 0 ? (
            <p className="text-muted-foreground italic text-sm">
              No tenés objetos en tu inventario.
            </p>
          ) : (
            <ul className="fuente-narrativa grid gap-2">
              {inventario.map((item, idx) => (
                <li
                  key={idx}
                  className="flex items-center gap-2 p-2 bg-muted rounded-md text-sm"
                >
                  <span className="text-muted-foreground">•</span>
                  {capitalizar(item)}
                </li>
              ))}
            </ul>
          )}
        </DialogContent>
      </Dialog>

      <AuthModal open={showAuth} onOpenChange={setShowAuth} />

      <SettingsSheet open={showSettings} onOpenChange={setShowSettings} />
    </header>
  );
}
